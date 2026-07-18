"""Tests for the reranker service.

Tests cross-encoder reranking with mocked model to avoid
downloading the actual model during tests.
"""

from unittest.mock import MagicMock, patch, AsyncMock
import numpy as np
import pytest

from app.services.vector_store import VectorSearchResult


class MockCrossEncoder:
    """Mock cross-encoder for testing."""

    def __init__(self):
        self.predict_calls = []

    def predict(self, pairs, batch_size=16, show_progress_bar=False):
        """Mock predict that returns scores based on content length."""
        self.predict_calls.append(pairs)
        scores = []
        for query, content in pairs:
            # Simple heuristic: longer content gets higher score
            score = min(len(content) / 100.0, 1.0)
            scores.append(score)
        return np.array(scores)


class TestReranker:
    """Test CrossEncoderReranker service."""

    def test_reranker_singleton_pattern(self):
        """Verify reranker uses singleton pattern."""
        from app.services.reranker import CrossEncoderReranker

        instance1 = CrossEncoderReranker()
        instance2 = CrossEncoderReranker()
        assert instance1 is instance2

    @patch("app.services.reranker.settings")
    def test_reranker_is_enabled_from_config(self, mock_settings):
        """Verify reranking can be disabled via config."""
        from app.services.reranker import CrossEncoderReranker

        mock_settings.ENABLE_RERANKING = True
        reranker = CrossEncoderReranker()
        assert reranker.is_enabled is True

        mock_settings.ENABLE_RERANKING = False
        assert reranker.is_enabled is False

    @patch("app.services.reranker.CrossEncoder")
    @patch("app.services.reranker.settings")
    def test_rerank_with_mocked_model(self, mock_settings, mock_cross_encoder_class):
        """Test reranking with mocked cross-encoder model."""
        from app.services.reranker import CrossEncoderReranker

        mock_settings.RERANKER_MODEL = "test-model"
        mock_settings.RERANKER_DEVICE = "cpu"
        mock_settings.RERANK_BATCH_SIZE = 16
        mock_settings.RERANK_SCORE_THRESHOLD = 0.0
        mock_settings.RERANK_TOP_K = 3
        mock_settings.ENABLE_RERANKING = True

        mock_model = MockCrossEncoder()
        mock_cross_encoder_class.return_value = mock_model

        # Reset singleton
        CrossEncoderReranker._instance = None
        CrossEncoderReranker._model = None

        reranker = CrossEncoderReranker()

        candidates = [
            VectorSearchResult(
                chunk_id="chunk1",
                document_id="doc1",
                content="Short",
                score=0.8,
                metadata={},
            ),
            VectorSearchResult(
                chunk_id="chunk2",
                document_id="doc1",
                content="Medium length content here",
                score=0.6,
                metadata={},
            ),
            VectorSearchResult(
                chunk_id="chunk3",
                document_id="doc1",
                content="Very long content that should get the highest rerank score",
                score=0.4,
                metadata={},
            ),
        ]

        results, metrics = reranker.rerank("test query", candidates, top_k=2)

        assert len(results) == 2
        assert results[0].chunk_id == "chunk3"  # Longest content
        assert results[1].chunk_id == "chunk2"  # Medium content
        assert metrics.total_candidates == 3
        assert metrics.reranked_count == 3
        assert metrics.rerank_time_ms >= 0

        # Reset singleton
        CrossEncoderReranker._instance = None
        CrossEncoderReranker._model = None

    def test_rerank_empty_candidates(self):
        """Test reranking with empty candidates list."""
        from app.services.reranker import CrossEncoderReranker

        CrossEncoderReranker._instance = None
        CrossEncoderReranker._model = None

        reranker = CrossEncoderReranker()
        results, metrics = reranker.rerank("test query", [], top_k=5)

        assert len(results) == 0
        assert metrics.total_candidates == 0
        assert metrics.rerank_time_ms == 0

        CrossEncoderReranker._instance = None
        CrossEncoderReranker._model = None

    @patch("app.services.reranker.CrossEncoder")
    @patch("app.services.reranker.settings")
    def test_rerank_with_score_threshold(self, mock_settings, mock_cross_encoder_class):
        """Test reranking filters results below score threshold."""
        from app.services.reranker import CrossEncoderReranker

        mock_settings.RERANKER_MODEL = "test-model"
        mock_settings.RERANKER_DEVICE = "cpu"
        mock_settings.RERANK_BATCH_SIZE = 16
        mock_settings.RERANK_SCORE_THRESHOLD = 0.5  # Filter low scores
        mock_settings.RERANK_TOP_K = 10
        mock_settings.ENABLE_RERANKING = True

        mock_model = MockCrossEncoder()
        mock_cross_encoder_class.return_value = mock_model

        CrossEncoderReranker._instance = None
        CrossEncoderReranker._model = None

        reranker = CrossEncoderReranker()

        candidates = [
            VectorSearchResult(
                chunk_id="chunk1",
                document_id="doc1",
                content="Short",  # Score ~0.06, below threshold
                score=0.8,
                metadata={},
            ),
            VectorSearchResult(
                chunk_id="chunk2",
                document_id="doc1",
                content="x" * 60,  # Score ~0.6, above threshold
                score=0.6,
                metadata={},
            ),
        ]

        results, metrics = reranker.rerank("test query", candidates, top_k=10)

        # chunk1 should be filtered out due to low score
        assert len(results) == 1
        assert results[0].chunk_id == "chunk2"
        assert metrics.filtered_count == 1

        CrossEncoderReranker._instance = None
        CrossEncoderReranker._model = None

    def test_get_model_info(self):
        """Test getting model information."""
        from app.services.reranker import CrossEncoderReranker

        CrossEncoderReranker._instance = None
        CrossEncoderReranker._model = None

        reranker = CrossEncoderReranker()
        info = reranker.get_model_info()

        assert "model_name" in info
        assert "device" in info
        assert "is_loaded" in info
        assert info["is_loaded"] is False

        CrossEncoderReranker._instance = None
        CrossEncoderReranker._model = None

    @patch("app.services.reranker.CrossEncoder")
    @patch("app.services.reranker.settings")
    def test_rerank_preserves_metadata(self, mock_settings, mock_cross_encoder_class):
        """Test that reranking preserves original metadata."""
        from app.services.reranker import CrossEncoderReranker

        mock_settings.RERANKER_MODEL = "test-model"
        mock_settings.RERANKER_DEVICE = "cpu"
        mock_settings.RERANK_BATCH_SIZE = 16
        mock_settings.RERANK_SCORE_THRESHOLD = 0.0
        mock_settings.RERANK_TOP_K = 5
        mock_settings.ENABLE_RERANKING = True

        mock_model = MockCrossEncoder()
        mock_cross_encoder_class.return_value = mock_model

        CrossEncoderReranker._instance = None
        CrossEncoderReranker._model = None

        reranker = CrossEncoderReranker()

        candidates = [
            VectorSearchResult(
                chunk_id="chunk1",
                document_id="doc1",
                content="Test content",
                score=0.8,
                metadata={"custom_field": "value", "page_number": 5},
            ),
        ]

        results, _ = reranker.rerank("test query", candidates, top_k=5)

        assert len(results) == 1
        assert results[0].metadata["custom_field"] == "value"
        assert results[0].metadata["page_number"] == 5
        assert "rerank_score" in results[0].metadata
        assert "original_score" in results[0].metadata

        CrossEncoderReranker._instance = None
        CrossEncoderReranker._model = None
