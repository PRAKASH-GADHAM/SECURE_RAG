"""Tests for RAG service.

Tests retrieval orchestration, source citation, and integration.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat import SourceDocument
from app.services.rag import RAGService, RAGQueryResult
from app.services.source_citation import SourceCitationBuilder, source_citation_builder
from app.services.vector_store import VectorSearchResult


class TestSourceCitationBuilder:
    """Tests for source citation building."""

    def test_build_sources_basic(self):
        """Test building sources from search results."""
        results = [
            VectorSearchResult(
                chunk_id="c1",
                document_id="d1",
                content="Test content about AI",
                score=0.95,
                metadata={"filename": "ai.pdf", "page_number": "5", "section": ""},
            ),
            VectorSearchResult(
                chunk_id="c2",
                document_id="d1",
                content="More AI content",
                score=0.80,
                metadata={"filename": "ai.pdf", "page_number": "", "section": "Introduction"},
            ),
        ]

        sources = SourceCitationBuilder.build_sources(results, max_sources=5)

        assert len(sources) == 2
        assert isinstance(sources[0], SourceDocument)
        assert sources[0].document_id == "d1"
        assert sources[0].document_name == "ai.pdf"
        assert sources[0].chunk_id == "c1"
        assert sources[0].score == 0.95
        assert sources[0].page_number == 5
        assert sources[0].section is None  # empty string -> None

    def test_build_sources_with_section(self):
        """Test that section metadata is preserved."""
        results = [
            VectorSearchResult(
                chunk_id="c1",
                document_id="d1",
                content="content",
                score=0.9,
                metadata={"filename": "doc.pdf", "section": "Chapter 1"},
            ),
        ]

        sources = SourceCitationBuilder.build_sources(results)
        assert sources[0].section == "Chapter 1"

    def test_build_sources_respects_max(self):
        """Test that max_sources limits output."""
        results = [
            VectorSearchResult(
                chunk_id=f"c{i}", document_id="d1", content="c",
                score=0.9 - i * 0.1, metadata={"filename": "doc.pdf"},
            )
            for i in range(10)
        ]

        sources = SourceCitationBuilder.build_sources(results, max_sources=3)
        assert len(sources) == 3

    def test_build_sources_empty(self):
        """Test building sources from empty results."""
        sources = SourceCitationBuilder.build_sources([])
        assert sources == []

    def test_build_context_string(self):
        """Test context string building."""
        results = [
            VectorSearchResult(
                chunk_id="c1",
                document_id="d1",
                content="Machine learning is a subset of AI.",
                score=0.95,
                metadata={"filename": "ml.pdf", "page_number": "3"},
            ),
        ]

        context = SourceCitationBuilder.build_context_string(results)

        assert "[Source 1:" in context
        assert "ml.pdf" in context
        assert "page 3" in context
        assert "Machine learning" in context

    def test_build_context_string_empty(self):
        """Test context string with no results."""
        context = SourceCitationBuilder.build_context_string([])
        assert context == "No relevant context found."

    def test_build_context_string_token_limit(self):
        """Test that context respects token limit."""
        results = [
            VectorSearchResult(
                chunk_id=f"c{i}", document_id="d1",
                content="word " * 500,  # ~500 tokens per chunk
                score=0.9, metadata={"filename": "doc.pdf"},
            )
            for i in range(10)
        ]

        context = SourceCitationBuilder.build_context_string(
            results, max_tokens_hint=100
        )

        # Should be limited (roughly 100 tokens * 4 chars = 400 chars minimum)
        assert len(context) < 10000

    def test_deduplicate_sources(self):
        """Test source deduplication."""
        sources = [
            SourceDocument(
                document_id="d1", document_name="doc.pdf",
                chunk_id="c1", content="A", score=0.9,
            ),
            SourceDocument(
                document_id="d1", document_name="doc.pdf",
                chunk_id="c1", content="A", score=0.9,
            ),
            SourceDocument(
                document_id="d1", document_name="doc.pdf",
                chunk_id="c2", content="B", score=0.8,
            ),
        ]

        deduped = SourceCitationBuilder.deduplicate_sources(sources)
        assert len(deduped) == 2


class TestRAGQueryResult:
    """Tests for RAGQueryResult dataclass."""

    def test_rag_query_result_fields(self):
        """Test that RAGQueryResult has expected fields."""
        result = RAGQueryResult(
            query="test query",
            results=[],
            sources_json="[]",
            context_string="context",
            total_chunks=0,
            user_id="user-1",
            retrieval_mode="hybrid",
        )

        assert result.query == "test query"
        assert result.retrieval_mode == "hybrid"
        assert result.total_chunks == 0


class TestRAGServiceConfig:
    """Tests for RAG service configuration building."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = RAGService()

    @patch("app.services.rag.settings")
    def test_build_config_default(self, mock_settings):
        """Test default config from settings."""
        mock_settings.TOP_K_RETRIEVAL = 10
        mock_settings.TOP_K_RERANK = 5
        mock_settings.RETRIEVAL_MODE = "hybrid"
        mock_settings.RRF_K = 60
        mock_settings.DENSE_WEIGHT = 0.7
        mock_settings.BM25_WEIGHT = 0.3

        config = self.service._build_config()

        assert config.mode == RetrievalMode.HYBRID
        assert config.top_k_final == 5
        assert config.rrf_k == 60

    def test_build_config_custom_top_k(self):
        """Test custom top_k overrides config."""
        config = self.service._build_config(top_k=15)
        assert config.top_k_final == 15

    def test_build_config_custom_mode(self):
        """Test custom mode overrides config."""
        config = self.service._build_config(retrieval_mode="dense")
        assert config.mode == RetrievalMode.DENSE

    def test_build_config_invalid_mode_falls_back(self):
        """Test invalid mode falls back to hybrid."""
        config = self.service._build_config(retrieval_mode="invalid")
        assert config.mode == RetrievalMode.HYBRID

    @patch("app.services.rag.settings")
    def test_build_config_bm25_mode(self, mock_settings):
        """Test BM25 mode config."""
        mock_settings.TOP_K_RETRIEVAL = 10
        mock_settings.TOP_K_RERANK = 5
        mock_settings.RETRIEVAL_MODE = "hybrid"
        mock_settings.RRF_K = 60
        mock_settings.DENSE_WEIGHT = 0.7
        mock_settings.BM25_WEIGHT = 0.3

        config = self.service._build_config(retrieval_mode="bm25")
        assert config.mode == RetrievalMode.BM25
