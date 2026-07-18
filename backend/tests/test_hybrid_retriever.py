"""Tests for hybrid retriever service.

Tests RRF fusion, retrieval modes, and configuration.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.hybrid_retriever import (
    HybridRetriever,
    HybridSearchConfig,
    RetrievalMode,
    RetrievalResult,
)
from app.services.vector_store import VectorSearchResult


class TestHybridSearchConfig:
    """Tests for HybridSearchConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = HybridSearchConfig()
        assert config.mode == RetrievalMode.HYBRID
        assert config.rrf_k == 60
        assert config.dense_weight == 0.7
        assert config.bm25_weight == 0.3

    def test_custom_config(self):
        """Test custom configuration."""
        config = HybridSearchConfig(
            mode=RetrievalMode.DENSE,
            top_k_dense=20,
            top_k_final=3,
        )
        assert config.mode == RetrievalMode.DENSE
        assert config.top_k_dense == 20
        assert config.top_k_final == 3


class TestRRFFusion:
    """Tests for Reciprocal Rank Fusion."""

    def setup_method(self):
        """Set up test fixtures."""
        self.retriever = HybridRetriever()

    def _make_result(self, chunk_id: str, doc_id: str = "d1", content: str = "content") -> VectorSearchResult:
        """Helper to create a VectorSearchResult."""
        return VectorSearchResult(
            chunk_id=chunk_id,
            document_id=doc_id,
            content=content,
            score=0.5,
            metadata={"filename": "test.pdf"},
        )

    def test_rrf_fusion_basic(self):
        """Test basic RRF fusion of two result lists."""
        dense = [
            self._make_result("c1", content="dense first"),
            self._make_result("c2", content="dense second"),
            self._make_result("c3", content="dense third"),
        ]
        bm25 = [
            self._make_result("c2", content="bm25 first"),
            self._make_result("c1", content="bm25 second"),
            self._make_result("c4", content="bm25 third"),
        ]

        fused = self.retriever._rrf_fusion(dense, bm25, k=60)

        # c1 and c2 appear in both lists, so should have higher scores
        chunk_ids = [r.chunk_id for r in fused]
        assert "c1" in chunk_ids
        assert "c2" in chunk_ids
        assert "c3" in chunk_ids
        assert "c4" in chunk_ids

        # c1 or c2 should be first (they appear in both lists)
        assert fused[0].chunk_id in ("c1", "c2")

    def test_rrf_fusion_empty_dense(self):
        """Test RRF fusion when dense results are empty."""
        bm25 = [
            self._make_result("c1"),
            self._make_result("c2"),
        ]

        fused = self.retriever._rrf_fusion([], bm25, k=60)

        assert len(fused) == 2
        assert fused[0].chunk_id == "c1"

    def test_rrf_fusion_empty_bm25(self):
        """Test RRF fusion when BM25 results are empty."""
        dense = [
            self._make_result("c1"),
            self._make_result("c2"),
        ]

        fused = self.retriever._rrf_fusion(dense, [], k=60)

        assert len(fused) == 2
        assert fused[0].chunk_id == "c1"

    def test_rrf_fusion_both_empty(self):
        """Test RRF fusion when both result lists are empty."""
        fused = self.retriever._rrf_fusion([], [], k=60)
        assert fused == []

    def test_rrf_fusion_deduplicates(self):
        """Test that RRF fusion deduplicates by chunk_id."""
        dense = [self._make_result("c1"), self._make_result("c2")]
        bm25 = [self._make_result("c1"), self._make_result("c3")]

        fused = self.retriever._rrf_fusion(dense, bm25, k=60)

        chunk_ids = [r.chunk_id for r in fused]
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_rrf_fusion_rrf_score_in_metadata(self):
        """Test that RRF score is added to metadata."""
        dense = [self._make_result("c1")]
        bm25 = [self._make_result("c1")]

        fused = self.retriever._rrf_fusion(dense, bm25, k=60)

        assert len(fused) == 1
        assert "rrf_score" in fused[0].metadata
        assert "dense_rank" in fused[0].metadata
        assert "bm25_rank" in fused[0].metadata
        assert fused[0].metadata["retrieval_method"] == "hybrid"

    def test_rrf_fusion_sorted_by_score(self):
        """Test that results are sorted by RRF score descending."""
        dense = [
            self._make_result("c1"),
            self._make_result("c2"),
            self._make_result("c3"),
        ]
        bm25 = [
            self._make_result("c1"),  # c1 in both = highest
            self._make_result("c4"),
            self._make_result("c5"),
        ]

        fused = self.retriever._rrf_fusion(dense, bm25, k=60)

        scores = [r.score for r in fused]
        assert scores == sorted(scores, reverse=True)

    def test_rrf_fusion_weighted(self):
        """Test that weights affect the fusion scores."""
        dense = [self._make_result("c1")]
        bm25 = [self._make_result("c2")]

        # High dense weight
        fused_heavy_dense = self.retriever._rrf_fusion(
            dense, bm25, k=60, dense_weight=0.9, bm25_weight=0.1
        )

        # High bm25 weight
        fused_heavy_bm25 = self.retriever._rrf_fusion(
            dense, bm25, k=60, dense_weight=0.1, bm25_weight=0.9
        )

        # c1 should be higher with heavy dense weight
        c1_score_heavy_dense = next(
            r.score for r in fused_heavy_dense if r.chunk_id == "c1"
        )
        c1_score_heavy_bm25 = next(
            r.score for r in fused_heavy_bm25 if r.chunk_id == "c1"
        )
        assert c1_score_heavy_dense > c1_score_heavy_bm25


class TestRetrievalMode:
    """Tests for RetrievalMode enum."""

    def test_mode_values(self):
        """Test that mode enum has correct values."""
        assert RetrievalMode.DENSE.value == "dense"
        assert RetrievalMode.BM25.value == "bm25"
        assert RetrievalMode.HYBRID.value == "hybrid"

    def test_mode_from_string(self):
        """Test creating mode from string."""
        assert RetrievalMode("dense") == RetrievalMode.DENSE
        assert RetrievalMode("bm25") == RetrievalMode.BM25
        assert RetrievalMode("hybrid") == RetrievalMode.HYBRID
