"""Hybrid retriever service.

Combines dense (vector similarity) and BM25 (keyword) retrieval
using Reciprocal Rank Fusion (RRF) to produce a unified ranked result list.

RRF Formula:
    score(d) = sum(1 / (k + rank_i(d))) for each retrieval method i

Where k is a constant (default 60) that controls how much weight
is given to lower-ranked documents.

Pipeline:
    Query
       ↓
    Metadata Filtering
       ↓
    Dense Retrieval (BGE-M3)
       ↓
    BM25 Retrieval
       ↓
    Reciprocal Rank Fusion (RRF)
       ↓
    Cross-Encoder Re-ranking (optional)
       ↓
    Final Top-K Context
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services.bm25_retriever import bm25_retriever
from app.services.embedding import embedding_service
from app.services.metadata_filter import MetadataFilter
from app.services.vector_store import vector_store, VectorSearchResult
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RetrievalMode(str, Enum):
    """Retrieval mode options."""

    DENSE = "dense"
    BM25 = "bm25"
    HYBRID = "hybrid"


@dataclass
class HybridSearchConfig:
    """Configuration for hybrid retrieval."""

    mode: RetrievalMode = RetrievalMode.HYBRID
    top_k_dense: int = 10
    top_k_bm25: int = 10
    top_k_final: int = 5
    rrf_k: int = 60
    dense_weight: float = 0.7
    bm25_weight: float = 0.3
    enable_reranking: bool = True
    metadata_filters: Optional[dict[str, Any]] = None


@dataclass
class RetrievalMetrics:
    """Metrics from retrieval operation."""

    dense_time_ms: int = 0
    bm25_time_ms: int = 0
    fusion_time_ms: int = 0
    rerank_time_ms: int = 0
    total_time_ms: int = 0
    dense_candidates: int = 0
    bm25_candidates: int = 0
    fused_candidates: int = 0
    final_results: int = 0
    metadata_filters_applied: bool = False


@dataclass
class RetrievalResult:
    """Unified retrieval result with source tracking."""

    query: str
    results: list[VectorSearchResult]
    total_results: int
    mode: RetrievalMode
    user_id: str
    metrics: RetrievalMetrics = field(default_factory=RetrievalMetrics)


class HybridRetriever:
    """Service for hybrid retrieval combining dense and BM25 search.

    Uses Reciprocal Rank Fusion (RRF) to merge results from
    multiple retrieval methods into a single ranked list.

    Supports metadata filtering before retrieval and optional
    cross-encoder reranking after fusion.
    """

    def __init__(self):
        """Initialize the hybrid retriever."""
        self.dense_store = vector_store
        self.bm25 = bm25_retriever
        self.embedder = embedding_service
        self._reranker = None
        logger.info("Hybrid Retriever initialized")

    @property
    def reranker(self):
        """Lazy load the reranker service."""
        if self._reranker is None:
            from app.services.reranker import reranker
            self._reranker = reranker
        return self._reranker

    async def retrieve(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        config: Optional[HybridSearchConfig] = None,
        document_ids: Optional[list[str]] = None,
    ) -> RetrievalResult:
        """Execute retrieval based on the configured mode.

        Pipeline: Metadata Filtering → Dense/BM25 → RRF → Reranking

        Args:
            db: Database session (for BM25 index building).
            user_id: User ID for namespace isolation.
            query: Query text.
            config: Retrieval configuration. Uses defaults if None.
            document_ids: Optional filter by specific document IDs.

        Returns:
            RetrievalResult with ranked search results and metrics.
        """
        start_time = time.time()
        metrics = RetrievalMetrics()

        if config is None:
            config = HybridSearchConfig(
                top_k_dense=settings.TOP_K_RETRIEVAL,
                top_k_bm25=settings.TOP_K_RETRIEVAL,
                top_k_final=settings.TOP_K_RERANK,
            )

        if config.metadata_filters:
            logger.info(f"Metadata filters applied: {config.metadata_filters}")
            metrics.metadata_filters_applied = True

        logger.info(
            f"Retrieval: mode={config.mode.value}, user={user_id}, "
            f"query_len={len(query)}, filters={bool(config.metadata_filters)}"
        )

        if config.mode == RetrievalMode.DENSE:
            results = await self._dense_retrieve(
                user_id, query, config, document_ids, metrics
            )
        elif config.mode == RetrievalMode.BM25:
            results = await self._bm25_retrieve(
                db, user_id, query, config, document_ids, metrics
            )
        else:
            results = await self._hybrid_retrieve(
                db, user_id, query, config, document_ids, metrics
            )

        if config.enable_reranking and settings.ENABLE_RERANKING and results:
            results, rerank_metrics = self._apply_reranking(query, results, config)
            metrics.rerank_time_ms = rerank_metrics.rerank_time_ms

        metrics.total_time_ms = int((time.time() - start_time) * 1000)
        metrics.final_results = len(results)

        logger.info(
            f"Retrieval completed: mode={config.mode.value}, "
            f"results={len(results)}, total_time={metrics.total_time_ms}ms"
        )

        return RetrievalResult(
            query=query,
            results=results,
            total_results=len(results),
            mode=config.mode,
            user_id=user_id,
            metrics=metrics,
        )

    async def _dense_retrieve(
        self,
        user_id: str,
        query: str,
        config: HybridSearchConfig,
        document_ids: Optional[list[str]] = None,
        metrics: Optional[RetrievalMetrics] = None,
    ) -> list[VectorSearchResult]:
        """Execute dense (vector similarity) retrieval.

        Args:
            user_id: User ID.
            query: Query text.
            config: Search configuration.
            document_ids: Optional document ID filter.
            metrics: Metrics to update.

        Returns:
            Ranked search results from vector similarity.
        """
        start_time = time.time()

        query_embedding = self.embedder.embed_query(query)

        results = self.dense_store.search(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=config.top_k_dense,
            document_ids=document_ids,
        )

        if metrics:
            metrics.dense_time_ms = int((time.time() - start_time) * 1000)
            metrics.dense_candidates = len(results)

        logger.info(
            f"Dense retrieval: {len(results)} results, "
            f"time={metrics.dense_time_ms if metrics else 0}ms"
        )
        return results

    async def _bm25_retrieve(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        config: HybridSearchConfig,
        document_ids: Optional[list[str]] = None,
        metrics: Optional[RetrievalMetrics] = None,
    ) -> list[VectorSearchResult]:
        """Execute BM25 (keyword) retrieval.

        Args:
            db: Database session.
            user_id: User ID.
            query: Query text.
            config: Search configuration.
            document_ids: Optional document ID filter.
            metrics: Metrics to update.

        Returns:
            Ranked search results from BM25.
        """
        start_time = time.time()

        index = await self.bm25.get_or_build_index(db, user_id, document_ids)
        if index is None:
            logger.info("BM25 index empty, returning no results")
            if metrics:
                metrics.bm25_time_ms = int((time.time() - start_time) * 1000)
            return []

        results = self.bm25.search(query, index, top_k=config.top_k_bm25)

        if metrics:
            metrics.bm25_time_ms = int((time.time() - start_time) * 1000)
            metrics.bm25_candidates = len(results)

        logger.info(
            f"BM25 retrieval: {len(results)} results, "
            f"time={metrics.bm25_time_ms if metrics else 0}ms"
        )
        return results

    async def _hybrid_retrieve(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        config: HybridSearchConfig,
        document_ids: Optional[list[str]] = None,
        metrics: Optional[RetrievalMetrics] = None,
    ) -> list[VectorSearchResult]:
        """Execute hybrid retrieval with Reciprocal Rank Fusion.

        Combines dense and BM25 results using RRF scoring.

        Args:
            db: Database session.
            user_id: User ID.
            query: Query text.
            config: Search configuration.
            document_ids: Optional document ID filter.
            metrics: Metrics to update.

        Returns:
            Fused and ranked search results.
        """
        fusion_start = time.time()

        dense_results = await self._dense_retrieve(user_id, query, config, document_ids, metrics)
        bm25_results = await self._bm25_retrieve(db, user_id, query, config, document_ids, metrics)

        if not dense_results and not bm25_results:
            if metrics:
                metrics.fusion_time_ms = int((time.time() - fusion_start) * 1000)
            return []

        if not dense_results:
            if metrics:
                metrics.fusion_time_ms = int((time.time() - fusion_start) * 1000)
                metrics.fused_candidates = len(bm25_results[:config.top_k_final])
            return bm25_results[:config.top_k_final]

        if not bm25_results:
            if metrics:
                metrics.fusion_time_ms = int((time.time() - fusion_start) * 1000)
                metrics.fused_candidates = len(dense_results[:config.top_k_final])
            return dense_results[:config.top_k_final]

        fused = self._rrf_fusion(
            dense_results,
            bm25_results,
            k=config.rrf_k,
            dense_weight=config.dense_weight,
            bm25_weight=config.bm25_weight,
        )

        results = fused[:config.top_k_final]

        if metrics:
            metrics.fusion_time_ms = int((time.time() - fusion_start) * 1000)
            metrics.fused_candidates = len(results)

        logger.info(
            f"Hybrid retrieval: dense={len(dense_results)}, "
            f"bm25={len(bm25_results)}, fused={len(results)}"
        )

        return results

    def _rrf_fusion(
        self,
        dense_results: list[VectorSearchResult],
        bm25_results: list[VectorSearchResult],
        k: int = 60,
        dense_weight: float = 0.7,
        bm25_weight: float = 0.3,
    ) -> list[VectorSearchResult]:
        """Combine results using Reciprocal Rank Fusion.

        RRF Formula:
            score(d) = w1 * (1 / (k + rank_dense(d)))
                      + w2 * (1 / (k + rank_bm25(d)))

        Args:
            dense_results: Results from dense retrieval.
            bm25_results: Results from BM25 retrieval.
            k: RRF constant.
            dense_weight: Weight for dense results.
            bm25_weight: Weight for BM25 results.

        Returns:
            Fused results sorted by combined RRF score.
        """
        dense_ranks = {
            r.chunk_id: rank + 1
            for rank, r in enumerate(dense_results)
        }
        bm25_ranks = {
            r.chunk_id: rank + 1
            for rank, r in enumerate(bm25_results)
        }

        result_map: dict[str, VectorSearchResult] = {}
        for r in dense_results + bm25_results:
            if r.chunk_id not in result_map:
                result_map[r.chunk_id] = r

        all_chunk_ids = set(dense_ranks.keys()) | set(bm25_ranks.keys())
        scored_results = []

        for chunk_id in all_chunk_ids:
            dense_score = 0.0
            bm25_score = 0.0

            if chunk_id in dense_ranks:
                dense_score = dense_weight / (k + dense_ranks[chunk_id])

            if chunk_id in bm25_ranks:
                bm25_score = bm25_weight / (k + bm25_ranks[chunk_id])

            rrf_score = dense_score + bm25_score

            original = result_map[chunk_id]
            scored_results.append(
                VectorSearchResult(
                    chunk_id=original.chunk_id,
                    document_id=original.document_id,
                    content=original.content,
                    score=rrf_score,
                    metadata={
                        **original.metadata,
                        "rrf_score": rrf_score,
                        "dense_rank": dense_ranks.get(chunk_id),
                        "bm25_rank": bm25_ranks.get(chunk_id),
                        "retrieval_method": "hybrid",
                    },
                )
            )

        scored_results.sort(key=lambda r: r.score, reverse=True)

        return scored_results

    def _apply_reranking(
        self,
        query: str,
        candidates: list[VectorSearchResult],
        config: HybridSearchConfig,
    ) -> tuple[list[VectorSearchResult], Any]:
        """Apply cross-encoder reranking to candidates.

        Args:
            query: User query.
            candidates: Candidate documents to rerank.
            config: Search configuration.

        Returns:
            Tuple of (reranked results, rerank metrics).
        """
        from app.services.reranker import reranker

        rerank_results, metrics = reranker.rerank(
            query=query,
            candidates=candidates,
            top_k=config.top_k_final,
        )

        vector_results = []
        for rr in rerank_results:
            vector_results.append(
                VectorSearchResult(
                    chunk_id=rr.chunk_id,
                    document_id=rr.document_id,
                    content=rr.content,
                    score=rr.rerank_score,
                    metadata=rr.metadata,
                )
            )

        return vector_results, metrics


# Module-level instance
hybrid_retriever = HybridRetriever()
