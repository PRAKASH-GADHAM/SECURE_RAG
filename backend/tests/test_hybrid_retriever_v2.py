"""Tests for the RAG service with reranking and metadata filtering.

Tests the complete RAG pipeline including metadata filtering,
retrieval, and reranking integration.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.services.hybrid_retriever import (
    HybridSearchConfig,
    HybridRetriever,
    RetrievalMetrics,
    RetrievalMode,
    RetrievalResult,
)
from app.services.vector_store import VectorSearchResult


class TestHybridSearchConfig:
    """Test HybridSearchConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = HybridSearchConfig()
        assert config.mode == RetrievalMode.HYBRID
        assert config.enable_reranking is True
        assert config.metadata_filters is None

    def test_config_with_metadata_filters(self):
        """Test configuration with metadata filters."""
        filters = {"section": "introduction"}
        config = HybridSearchConfig(metadata_filters=filters)
        assert config.metadata_filters == filters

    def test_config_without_reranking(self):
        """Test configuration with reranking disabled."""
        config = HybridSearchConfig(enable_reranking=False)
        assert config.enable_reranking is False


class TestRetrievalMetrics:
    """Test RetrievalMetrics."""

    def test_default_metrics(self):
        """Test default metrics values."""
        metrics = RetrievalMetrics()
        assert metrics.dense_time_ms == 0
        assert metrics.bm25_time_ms == 0
        assert metrics.fusion_time_ms == 0
        assert metrics.rerank_time_ms == 0
        assert metrics.total_time_ms == 0
        assert metrics.metadata_filters_applied is False


class TestRetrievalResult:
    """Test RetrievalResult."""

    def test_retrieval_result_creation(self):
        """Test creating a retrieval result."""
        result = RetrievalResult(
            query="test query",
            results=[],
            total_results=0,
            mode=RetrievalMode.HYBRID,
            user_id="user123",
        )
        assert result.query == "test query"
        assert result.total_results == 0
        assert result.metrics is not None


class TestHybridRetriever:
    """Test HybridRetriever service."""

    def test_retriever_initialization(self):
        """Test retriever initialization."""
        from app.services.hybrid_retriever import HybridRetriever
        retriever = HybridRetriever()
        assert retriever.dense_store is not None
        assert retriever.bm25 is not None
        assert retriever.embedder is not None

    def test_rrf_fusion_basic(self):
        """Test basic RRF fusion."""
        from app.services.hybrid_retriever import HybridRetriever

        retriever = HybridRetriever()

        dense_results = [
            VectorSearchResult(
                chunk_id="c1", document_id="d1", content="a", score=0.9, metadata={}
            ),
            VectorSearchResult(
                chunk_id="c2", document_id="d1", content="b", score=0.8, metadata={}
            ),
        ]

        bm25_results = [
            VectorSearchResult(
                chunk_id="c2", document_id="d1", content="b", score=0.7, metadata={}
            ),
            VectorSearchResult(
                chunk_id="c3", document_id="d1", content="c", score=0.6, metadata={}
            ),
        ]

        fused = retriever._rrf_fusion(dense_results, bm25_results)

        assert len(fused) == 3  # c1, c2, c3
        # c2 appears in both, should have highest combined score
        assert fused[0].chunk_id == "c2"

    def test_rrf_fusion_empty_results(self):
        """Test RRF fusion with empty results."""
        from app.services.hybrid_retriever import HybridRetriever

        retriever = HybridRetriever()
        fused = retriever._rrf_fusion([], [])
        assert len(fused) == 0

    def test_rrf_fusion_only_dense(self):
        """Test RRF fusion with only dense results."""
        from app.services.hybrid_retriever import HybridRetriever

        retriever = HybridRetriever()

        dense_results = [
            VectorSearchResult(
                chunk_id="c1", document_id="d1", content="a", score=0.9, metadata={}
            ),
        ]

        fused = retriever._rrf_fusion(dense_results, [])
        assert len(fused) == 1
        assert fused[0].chunk_id == "c1"

    def test_rrf_fusion_only_bm25(self):
        """Test RRF fusion with only BM25 results."""
        from app.services.hybrid_retriever import HybridRetriever

        retriever = HybridRetriever()

        bm25_results = [
            VectorSearchResult(
                chunk_id="c1", document_id="d1", content="a", score=0.9, metadata={}
            ),
        ]

        fused = retriever._rrf_fusion([], bm25_results)
        assert len(fused) == 1
        assert fused[0].chunk_id == "c1"

    def test_rrf_fusion_preserves_metadata(self):
        """Test that RRF fusion preserves original metadata."""
        from app.services.hybrid_retriever import HybridRetriever

        retriever = HybridRetriever()

        dense_results = [
            VectorSearchResult(
                chunk_id="c1",
                document_id="d1",
                content="a",
                score=0.9,
                metadata={"page_number": 5, "section": "intro"},
            ),
        ]

        fused = retriever._rrf_fusion(dense_results, [])

        assert fused[0].metadata["page_number"] == 5
        assert fused[0].metadata["section"] == "intro"
        assert "rrf_score" in fused[0].metadata
        assert "dense_rank" in fused[0].metadata

    @pytest.mark.asyncio
    async def test_dense_retrieve_with_metrics(self):
        """Test dense retrieval updates metrics."""
        from app.services.hybrid_retriever import HybridRetriever

        retriever = HybridRetriever()
        retriever.dense_store = MagicMock()
        retriever.dense_store.search.return_value = [
            VectorSearchResult(
                chunk_id="c1", document_id="d1", content="a", score=0.9, metadata={}
            ),
        ]
        retriever.embedder = MagicMock()
        retriever.embedder.embed_query.return_value = [0.1] * 10

        metrics = RetrievalMetrics()
        config = HybridSearchConfig(mode=RetrievalMode.DENSE, top_k_dense=5)

        results = await retriever._dense_retrieve(
            "user1", "test query", config, metrics=metrics
        )

        assert len(results) == 1
        assert metrics.dense_candidates == 1
        assert metrics.dense_time_ms >= 0


class TestRAGServiceConfig:
    """Test RAG service configuration building."""

    def test_build_config_defaults(self):
        """Test building config with defaults."""
        from app.services.rag import RAGService

        service = RAGService()
        config = service._build_config()

        assert config.mode == RetrievalMode.HYBRID
        assert config.enable_reranking is True
        assert config.metadata_filters is None

    def test_build_config_with_reranking_disabled(self):
        """Test building config with reranking disabled."""
        from app.services.rag import RAGService

        service = RAGService()
        config = service._build_config(use_reranking=False)

        assert config.enable_reranking is False

    def test_build_config_with_metadata_filters(self):
        """Test building config with metadata filters."""
        from app.services.rag import RAGService

        service = RAGService()
        filters = {"section": "test"}
        config = service._build_config(metadata_filters=filters)

        assert config.metadata_filters == filters

    def test_build_config_invalid_mode_fallback(self):
        """Test that invalid mode falls back to hybrid."""
        from app.services.rag import RAGService

        service = RAGService()
        config = service._build_config(retrieval_mode="invalid_mode")

        assert config.mode == RetrievalMode.HYBRID
