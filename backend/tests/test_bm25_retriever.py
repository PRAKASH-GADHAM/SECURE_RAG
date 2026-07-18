"""Tests for BM25 retriever service.

Tests tokenization, index building, search, and caching.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.services.bm25_retriever import BM25Index, BM25Retriever


class TestBM25Tokenization:
    """Tests for BM25 text tokenization."""

    def test_tokenize_basic(self):
        """Test basic tokenization."""
        tokens = BM25Retriever.tokenize("Hello World Test")
        assert tokens == ["hello", "world", "test"]

    def test_tokenize_lowercase(self):
        """Test that tokens are lowercased."""
        tokens = BM25Retriever.tokenize("UPPERCASE lowerCase")
        assert all(t == t.lower() for t in tokens)

    def test_tokenize_filters_short_tokens(self):
        """Test that single-character tokens are filtered."""
        tokens = BM25Retriever.tokenize("a bb ccc d")
        assert "a" not in tokens
        assert "d" not in tokens
        assert "bb" in tokens
        assert "ccc" in tokens

    def test_tokenize_with_numbers(self):
        """Test tokenization preserves numbers."""
        tokens = BM25Retriever.tokenize("version 2.0 has 100 features")
        assert "2" in tokens
        assert "0" not in tokens  # single char filtered
        assert "100" in tokens
        assert "features" in tokens

    def test_tokenize_special_characters(self):
        """Test that special characters are ignored."""
        tokens = BM25Retriever.tokenize("hello@world.com test!#$%")
        assert "hello" in tokens
        assert "world" in tokens
        assert "com" in tokens
        assert "test" in tokens

    def test_tokenize_empty_string(self):
        """Test tokenizing empty string."""
        tokens = BM25Retriever.tokenize("")
        assert tokens == []

    def test_tokenize_unicode(self):
        """Test tokenization handles unicode gracefully."""
        tokens = BM25Retriever.tokenize("café résumé naïve")
        # Non-ascii chars may or may not match [a-z0-9]+
        assert isinstance(tokens, list)


class TestBM25Retriever:
    """Tests for BM25Retriever service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.retriever = BM25Retriever()

    def test_build_index_from_mock_data(self):
        """Test building index from pre-constructed data."""
        # Manually build an index to test search
        corpus = [
            "Machine learning is a subset of artificial intelligence",
            "Deep learning uses neural networks with many layers",
            "Natural language processing handles human language",
            "Computer vision analyzes visual data from cameras",
        ]

        tokenized = [BM25Retriever.tokenize(doc) for doc in corpus]
        bm25 = BM25Index(
            user_id="user-1",
            corpus=corpus,
            tokenized_corpus=tokenized,
            chunk_ids=["c1", "c2", "c3", "c4"],
            document_ids=["d1", "d1", "d1", "d1"],
            chunk_contents=corpus,
            chunk_metadatas=[
                {"document_id": "d1", "filename": "test.pdf"},
                {"document_id": "d1", "filename": "test.pdf"},
                {"document_id": "d1", "filename": "test.pdf"},
                {"document_id": "d1", "filename": "test.pdf"},
            ],
            bm25=None,  # Will be set below
        )

        from rank_bm25 import BM25Okapi
        bm25.bm25 = BM25Okapi(tokenized)

        # Search
        results = self.retriever.search("neural networks", bm25, top_k=2)

        assert len(results) == 2
        # "Deep learning uses neural networks" should be most relevant
        assert results[0].chunk_id == "c2"
        assert results[0].score > 0

    def test_search_empty_index(self):
        """Test search with empty index returns empty."""
        index = BM25Index(
            user_id="user-1",
            corpus=[],
            tokenized_corpus=[],
            chunk_ids=[],
            document_ids=[],
            chunk_contents=[],
            chunk_metadatas=[],
            bm25=None,
        )

        results = self.retriever.search("test query", index, top_k=5)
        assert results == []

    def test_search_empty_query(self):
        """Test search with empty query returns empty."""
        index = BM25Index(
            user_id="user-1",
            corpus=["test document"],
            tokenized_corpus=[["test", "document"]],
            chunk_ids=["c1"],
            document_ids=["d1"],
            chunk_contents=["test document"],
            chunk_metadatas=[{"document_id": "d1"}],
            bm25=None,
        )

        from rank_bm25 import BM25Okapi
        index.bm25 = BM25Okapi(index.tokenized_corpus)

        results = self.retriever.search("", index, top_k=5)
        assert results == []

    def test_search_scores_are_normalized(self):
        """Test that search scores are normalized to [0, 1]."""
        corpus = [
            "Python is a programming language",
            "Java is also a programming language",
            "Cats are animals",
        ]
        tokenized = [BM25Retriever.tokenize(doc) for doc in corpus]

        from rank_bm25 import BM25Okapi
        bm25_obj = BM25Okapi(tokenized)

        index = BM25Index(
            user_id="user-1",
            corpus=corpus,
            tokenized_corpus=tokenized,
            chunk_ids=["c1", "c2", "c3"],
            document_ids=["d1", "d1", "d2"],
            chunk_contents=corpus,
            chunk_metadatas=[{"document_id": "d1"}] * 3,
            bm25=bm25_obj,
        )

        results = self.retriever.search("Python programming", index, top_k=3)

        assert len(results) > 0
        for r in results:
            assert 0.0 <= r.score <= 1.0

    def test_cache_invalidation(self):
        """Test that cache invalidation works."""
        self.retriever._indexes["user-1:all"] = MagicMock()
        self.retriever._indexes["user-1:doc1"] = MagicMock()
        self.retriever._indexes["user-2:all"] = MagicMock()

        self.retriever.invalidate_cache("user-1")

        assert "user-1:all" not in self.retriever._indexes
        assert "user-1:doc1" not in self.retriever._indexes
        assert "user-2:all" in self.retriever._indexes

    def test_cache_validity(self):
        """Test cache TTL checking."""
        valid_index = MagicMock()
        valid_index.created_at = time.time()

        expired_index = MagicMock()
        expired_index.created_at = time.time() - 700  # > 600s TTL

        assert self.retriever._is_cache_valid(valid_index) is True
        assert self.retriever._is_cache_valid(expired_index) is False

    def test_get_cache_stats(self):
        """Test cache statistics."""
        self.retriever._indexes["u1:a"] = MagicMock()
        self.retriever._indexes["u1:a"].created_at = time.time()
        self.retriever._indexes["u1:b"] = MagicMock()
        self.retriever._indexes["u1:b"].created_at = time.time() - 700

        stats = self.retriever.get_cache_stats()
        assert stats["total_indexes"] == 2
        assert stats["valid_indexes"] == 1
        assert stats["expired_indexes"] == 1

    def test_search_returns_vector_search_results(self):
        """Test that search returns proper VectorSearchResult objects."""
        from app.services.vector_store import VectorSearchResult

        corpus = ["Test document about AI"]
        tokenized = [BM25Retriever.tokenize(doc) for doc in corpus]

        from rank_bm25 import BM25Okapi
        bm25_obj = BM25Okapi(tokenized)

        index = BM25Index(
            user_id="user-1",
            corpus=corpus,
            tokenized_corpus=tokenized,
            chunk_ids=["c1"],
            document_ids=["d1"],
            chunk_contents=corpus,
            chunk_metadatas=[{"document_id": "d1", "filename": "test.pdf"}],
            bm25=bm25_obj,
        )

        results = self.retriever.search("AI", index, top_k=1)

        assert len(results) == 1
        assert isinstance(results[0], VectorSearchResult)
        assert results[0].chunk_id == "c1"
        assert results[0].document_id == "d1"
        assert "document_id" in results[0].metadata
