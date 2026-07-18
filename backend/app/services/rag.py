"""RAG service.

Orchestrates the Retrieval-Augmented Generation pipeline:
- Query processing and input validation
- Metadata filtering
- Hybrid retrieval (dense + BM25 + RRF fusion)
- Cross-encoder reranking
- Source citation generation
- LLM generation via provider interface

Pipeline:
    Query
       ↓
    Input Validation & Sanitization
       ↓
    Metadata Filtering
       ↓
    Dense Retrieval (BGE-M3)
       ↓
    BM25 Retrieval
       ↓
    Reciprocal Rank Fusion (RRF)
       ↓
    Cross-Encoder Re-ranking
       ↓
    Final Top-K Context → LLM Generation
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services.guardrails.guardrail_models import OutputDecision
from app.services.guardrails.output_pipeline import output_pipeline
from app.services.hybrid_retriever import (
    HybridSearchConfig,
    HybridRetriever,
    RetrievalMetrics,
    RetrievalMode,
    RetrievalResult,
)
from app.services.llm.base import (
    LLMConfig,
    LLMProviderError,
    LLMResponse,
    LLMStreamChunk,
)
from app.services.llm.factory import get_llm_provider
from app.services.prompt_builder import prompt_builder
from app.services.security.security_models import RiskLevel, SecurityAction
from app.services.security.security_pipeline import security_pipeline
from app.services.source_citation import source_citation_builder
from app.services.vector_store import VectorSearchResult
from app.utils.logging import get_logger
from app.utils.validators import sanitize_input

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class RAGQueryResult:
    """Result from a RAG query."""

    query: str
    results: list[VectorSearchResult]
    sources_json: str
    context_string: str
    total_chunks: int
    user_id: str
    retrieval_mode: str
    metrics: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    reranking_enabled: bool = False
    # Generation fields
    answer: Optional[str] = None
    llm_response: Optional[LLMResponse] = None


class RAGService:
    """Service for RAG pipeline operations.

    Handles query processing, hybrid retrieval, reranking,
    source citation, and LLM generation.
    """

    def __init__(self):
        """Initialize the RAG service."""
        self.retriever = HybridRetriever()
        self.citation_builder = source_citation_builder
        self._llm_provider = None
        logger.info("RAG Service initialized")

    @property
    def llm_provider(self):
        """Lazy load the LLM provider."""
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider()
        return self._llm_provider

    async def retrieve(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        top_k: Optional[int] = None,
        retrieval_mode: Optional[str] = None,
        document_ids: Optional[list[str]] = None,
        use_reranking: bool = True,
        metadata_filters: Optional[dict[str, Any]] = None,
    ) -> RAGQueryResult:
        """Execute hybrid retrieval for a user query.

        Full pipeline: validation → filtering → retrieval → reranking → citation.

        Args:
            db: Database session (for BM25 index building).
            user_id: User ID for namespace isolation.
            query: User query text.
            top_k: Number of results to retrieve (overrides config).
            retrieval_mode: Retrieval mode override (dense/bm25/hybrid).
            document_ids: Optional filter by specific document IDs.
            use_reranking: Whether to apply cross-encoder reranking.
            metadata_filters: Optional metadata filters for document filtering.

        Returns:
            RAGQueryResult with retrieval results, context, and metrics.
        """
        start_time = time.time()

        logger.info(
            f"RAG retrieve: user={user_id}, mode={retrieval_mode or settings.RETRIEVAL_MODE}, "
            f"reranking={use_reranking}, filters={bool(metadata_filters)}"
        )

        sanitized_query = sanitize_input(query, max_length=5000)

        config = self._build_config(
            top_k, retrieval_mode, use_reranking, metadata_filters
        )

        retrieval_result = await self.retriever.retrieve(
            db=db,
            user_id=user_id,
            query=sanitized_query,
            config=config,
            document_ids=document_ids,
        )

        sources = self.citation_builder.build_sources(
            retrieval_result.results,
            max_sources=config.top_k_final,
        )

        context = self.citation_builder.build_context_string(
            retrieval_result.results,
            max_tokens_hint=settings.MAX_CONTEXT_LENGTH,
        )

        sources_json = json.dumps(
            [s.model_dump() for s in sources],
            default=str,
        )

        elapsed = time.time() - start_time
        logger.info(
            f"RAG retrieve completed: user={user_id}, "
            f"results={len(retrieval_result.results)}, "
            f"sources={len(sources)}, reranking={use_reranking}, "
            f"total_time={retrieval_result.metrics.total_time_ms}ms"
        )

        return RAGQueryResult(
            query=sanitized_query,
            results=retrieval_result.results,
            sources_json=sources_json,
            context_string=context,
            total_chunks=len(retrieval_result.results),
            user_id=user_id,
            retrieval_mode=config.mode.value,
            metrics=retrieval_result.metrics,
            reranking_enabled=use_reranking and settings.ENABLE_RERANKING,
        )

    async def generate(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        top_k: Optional[int] = None,
        retrieval_mode: Optional[str] = None,
        document_ids: Optional[list[str]] = None,
        use_reranking: bool = True,
        metadata_filters: Optional[dict[str, Any]] = None,
        conversation_history: Optional[list[dict[str, str]]] = None,
        stream: bool = False,
    ) -> RAGQueryResult:
        """Execute full RAG pipeline: retrieval + generation.

        Args:
            db: Database session.
            user_id: User ID for namespace isolation.
            query: User query text.
            top_k: Number of results to retrieve.
            retrieval_mode: Retrieval mode override.
            document_ids: Optional filter by document IDs.
            use_reranking: Whether to apply reranking.
            metadata_filters: Optional metadata filters.
            conversation_history: Optional chat history.
            stream: Whether to stream the response.

        Returns:
            RAGQueryResult with answer and metadata.
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(
            f"RAG generate: user={user_id}, request={request_id}, "
            f"stream={stream}"
        )

        # Step 1: Retrieve context
        rag_result = await self.retrieve(
            db=db,
            user_id=user_id,
            query=query,
            top_k=top_k,
            retrieval_mode=retrieval_mode,
            document_ids=document_ids,
            use_reranking=use_reranking,
            metadata_filters=metadata_filters,
        )

        # Step 2: Security analysis
        security_result = security_pipeline.analyze(
            content=query,
            user_id=user_id,
            request_id=request_id,
            context=rag_result.context_string,
        )

        # Handle blocked requests
        if security_result.recommended_action == SecurityAction.BLOCK:
            logger.warning(
                f"Security BLOCK: user={user_id}, request={request_id}, "
                f"risk_score={security_result.risk_score}, "
                f"patterns={security_result.detected_patterns[:3]}"
            )
            rag_result.answer = (
                "I apologize, but your request has been blocked due to "
                "security concerns. Please rephrase your question."
            )
            rag_result.metadata = {
                "security_blocked": True,
                "risk_score": security_result.risk_score,
            }
            return rag_result

        # Sanitize if suspicious
        sanitized_query = query
        if security_result.recommended_action == SecurityAction.SANITIZE:
            logger.info(
                f"Security SANITIZE: user={user_id}, request={request_id}, "
                f"risk_score={security_result.risk_score}"
            )
            sanitized_query = sanitize_input(query, max_length=5000)

        # Step 3: Build prompt
        messages = prompt_builder.build_rag_prompt(
            query=sanitized_query,
            context=rag_result.context_string,
            conversation_history=conversation_history,
        )

        # Step 4: Generate response
        llm_config = LLMConfig(
            model=settings.OPENROUTER_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            stream=stream,
        )

        if stream:
            # For streaming, we return the result with a generator
            rag_result.llm_response = None
            rag_result.answer = None
            return rag_result

        try:
            llm_response = await self.llm_provider.generate(
                messages=messages,
                config=llm_config,
                request_id=request_id,
                user_id=user_id,
            )

            # Step 5: Apply output protection (guardrails)
            guardrail_result = output_pipeline.analyze(
                content=llm_response.content,
                user_id=user_id,
                request_id=request_id,
                context=rag_result.context_string,
            )

            # Handle blocked responses
            if guardrail_result.decision == OutputDecision.BLOCKED:
                logger.warning(
                    f"Output BLOCKED: user={user_id}, request={request_id}, "
                    f"decision={guardrail_result.decision.value}"
                )
                rag_result.answer = guardrail_result.processed_content
                rag_result.llm_response = llm_response
                rag_result.metadata = {
                    "guardrail_blocked": True,
                    "warnings": guardrail_result.warnings,
                }
                return rag_result

            # Use processed content (may be redacted/sanitized)
            rag_result.answer = guardrail_result.processed_content
            rag_result.llm_response = llm_response

            # Add warnings to metadata if any
            if guardrail_result.warnings:
                rag_result.metadata = {
                    "guardrail_warnings": guardrail_result.warnings,
                }

            logger.info(
                f"RAG generate completed: user={user_id}, "
                f"request={request_id}, "
                f"tokens={llm_response.usage.total_tokens}, "
                f"latency={llm_response.latency_ms}ms, "
                f"guardrail_decision={guardrail_result.decision.value}"
            )

        except LLMProviderError as e:
            logger.error(
                f"LLM generation failed: user={user_id}, "
                f"request={request_id}, error={str(e)}"
            )
            rag_result.answer = (
                "I apologize, but I encountered an error while generating "
                "a response. Please try again later."
            )

        return rag_result

    async def generate_stream(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        top_k: Optional[int] = None,
        retrieval_mode: Optional[str] = None,
        document_ids: Optional[list[str]] = None,
        use_reranking: bool = True,
        metadata_filters: Optional[dict[str, Any]] = None,
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Execute RAG pipeline with streaming generation.

        Args:
            db: Database session.
            user_id: User ID.
            query: User query.
            top_k: Number of results.
            retrieval_mode: Retrieval mode.
            document_ids: Optional document ID filter.
            use_reranking: Whether to rerank.
            metadata_filters: Optional metadata filters.
            conversation_history: Optional chat history.

        Yields:
            LLMStreamChunk objects as they are generated.
        """
        request_id = str(uuid.uuid4())

        logger.info(
            f"RAG stream: user={user_id}, request={request_id}"
        )

        # Retrieve context
        rag_result = await self.retrieve(
            db=db,
            user_id=user_id,
            query=query,
            top_k=top_k,
            retrieval_mode=retrieval_mode,
            document_ids=document_ids,
            use_reranking=use_reranking,
            metadata_filters=metadata_filters,
        )

        # Build prompt
        messages = prompt_builder.build_rag_prompt(
            query=rag_result.query,
            context=rag_result.context_string,
            conversation_history=conversation_history,
        )

        llm_config = LLMConfig(
            model=settings.OPENROUTER_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            stream=True,
        )

        # Stream responses
        async for chunk in self.llm_provider.generate_stream(
            messages=messages,
            config=llm_config,
            request_id=request_id,
            user_id=user_id,
        ):
            yield chunk

    def _build_config(
        self,
        top_k: Optional[int] = None,
        retrieval_mode: Optional[str] = None,
        use_reranking: bool = True,
        metadata_filters: Optional[dict[str, Any]] = None,
    ) -> HybridSearchConfig:
        """Build retrieval configuration from parameters and defaults.

        Args:
            top_k: Optional top_k override.
            retrieval_mode: Optional mode override.
            use_reranking: Whether to enable reranking.
            metadata_filters: Optional metadata filters.

        Returns:
            HybridSearchConfig with resolved values.
        """
        mode_str = retrieval_mode or settings.RETRIEVAL_MODE
        try:
            mode = RetrievalMode(mode_str)
        except ValueError:
            mode = RetrievalMode.HYBRID

        final_top_k = top_k or settings.TOP_K_RERANK

        return HybridSearchConfig(
            mode=mode,
            top_k_dense=settings.TOP_K_RETRIEVAL,
            top_k_bm25=settings.TOP_K_RETRIEVAL,
            top_k_final=final_top_k,
            rrf_k=settings.RRF_K,
            dense_weight=settings.DENSE_WEIGHT,
            bm25_weight=settings.BM25_WEIGHT,
            enable_reranking=use_reranking,
            metadata_filters=metadata_filters,
        )

    def get_user_stats(self, user_id: str) -> dict:
        """Get RAG statistics for a user.

        Args:
            user_id: User ID.

        Returns:
            Dictionary with user's RAG stats.
        """
        stats = self.retriever.dense_store.get_collection_stats(user_id)
        stats["bm25_cache"] = self.retriever.bm25.get_cache_stats()
        stats["llm_provider"] = self.llm_provider.get_model_info()
        return stats


# Module-level instance
rag_service = RAGService()
