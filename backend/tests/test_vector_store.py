"""Tests for vector store service.

Tests ChromaDB operations with mocked ChromaDB client.
"""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.services.vector_store import VectorStore, VectorSearchResult


class TestVectorStore:
    """Tests for the VectorStore service with mocked ChromaDB."""

    def setup_method(self):
        """Set up test fixtures with mocked ChromaDB."""
        self.store = VectorStore()
        self.mock_client = MagicMock()
        self.mock_collection = MagicMock()
        self.store._client = self.mock_client
        self.mock_client.get_or_create_collection.return_value = self.mock_collection

    def test_get_user_collection_creates_collection(self):
        """Test that user collection uses correct naming convention."""
        collection = self.store._get_user_collection("user-123")

        self.mock_client.get_or_create_collection.assert_called_with(
            name="user_user-123_documents",
            metadata={"hnsw:space": "cosine"},
        )

    def test_get_user_collection_caches(self):
        """Test that collections are cached after first creation."""
        c1 = self.store._get_user_collection("user-123")
        c2 = self.store._get_user_collection("user-123")

        assert c1 is c2
        # Should only call get_or_create once
        assert self.mock_client.get_or_create_collection.call_count == 1

    def test_add_chunks_empty_returns_zero(self):
        """Test that adding empty chunks returns 0."""
        count = self.store.add_chunks(
            user_id="user-1",
            document_id="doc-1",
            chunk_ids=[],
            contents=[],
            embeddings=[],
            metadatas=[],
        )
        assert count == 0

    def test_add_chunks_sanitizes_metadata(self):
        """Test that metadata values are sanitized for ChromaDB."""
        self.mock_collection.count.return_value = 0

        self.store.add_chunks(
            user_id="user-1",
            document_id="doc-1",
            chunk_ids=["c1"],
            contents=["test content"],
            embeddings=[[0.1, 0.2, 0.3]],
            metadatas=[{"key": "value", "nested": {"a": 1}, "none_val": None}],
        )

        call_kwargs = self.mock_collection.add.call_args[1]
        metadata = call_kwargs["metadatas"][0]
        assert metadata["key"] == "value"
        assert metadata["nested"] == "{'a': 1}"  # dict converted to string
        assert metadata["none_val"] == ""  # None converted to empty string

    def test_add_chunks_in_batches(self):
        """Test that large chunks are added in batches."""
        chunk_ids = [f"c{i}" for i in range(250)]
        contents = [f"content {i}" for i in range(250)]
        embeddings = [[0.1] * 10 for _ in range(250)]
        metadatas = [{"doc": "d1"} for _ in range(250)]

        count = self.store.add_chunks(
            user_id="user-1",
            document_id="doc-1",
            chunk_ids=chunk_ids,
            contents=contents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        assert count == 250
        # 250 / 100 = 3 batches
        assert self.mock_collection.add.call_count == 3

    def test_search_returns_results(self):
        """Test that search returns parsed results."""
        self.mock_collection.count.return_value = 10
        self.mock_collection.query.return_value = {
            "ids": [["c1", "c2"]],
            "documents": [["Content 1", "Content 2"]],
            "metadatas": [
                [{"document_id": "d1"}, {"document_id": "d1"}]
            ],
            "distances": [[0.2, 0.4]],
        }

        results = self.store.search(
            user_id="user-1",
            query_embedding=[0.1] * 10,
            top_k=2,
        )

        assert len(results) == 2
        assert isinstance(results[0], VectorSearchResult)
        assert results[0].chunk_id == "c1"
        assert results[0].document_id == "d1"
        assert results[0].score > results[1].score  # Sorted by score desc

    def test_search_empty_results(self):
        """Test search with no results."""
        self.mock_collection.count.return_value = 0
        self.mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        results = self.store.search(
            user_id="user-1",
            query_embedding=[0.1] * 10,
            top_k=5,
        )

        assert results == []

    def test_search_exception_returns_empty(self):
        """Test that search exceptions return empty list."""
        self.mock_collection.query.side_effect = Exception("Connection error")

        results = self.store.search(
            user_id="user-1",
            query_embedding=[0.1] * 10,
            top_k=5,
        )

        assert results == []

    def test_search_with_document_filter(self):
        """Test search with document ID filter."""
        self.mock_collection.count.return_value = 5
        self.mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        self.store.search(
            user_id="user-1",
            query_embedding=[0.1] * 10,
            top_k=5,
            document_ids=["doc-1"],
        )

        call_kwargs = self.mock_collection.query.call_args[1]
        assert call_kwargs["where"] == {"document_id": "doc-1"}

    def test_search_with_multiple_document_filter(self):
        """Test search with multiple document ID filter."""
        self.mock_collection.count.return_value = 5
        self.mock_collection.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        self.store.search(
            user_id="user-1",
            query_embedding=[0.1] * 10,
            top_k=5,
            document_ids=["doc-1", "doc-2"],
        )

        call_kwargs = self.mock_collection.query.call_args[1]
        assert call_kwargs["where"] == {"document_id": {"$in": ["doc-1", "doc-2"]}}

    def test_delete_document(self):
        """Test deleting a document's chunks."""
        self.mock_collection.get.return_value = {
            "ids": ["c1", "c2", "c3"],
            "metadatas": [{"document_id": "d1"}] * 3,
        }

        deleted = self.store.delete_document("user-1", "doc-1")

        assert deleted == 3
        self.mock_collection.delete.assert_called_once_with(ids=["c1", "c2", "c3"])

    def test_delete_document_no_chunks(self):
        """Test deleting a document with no chunks."""
        self.mock_collection.get.return_value = {"ids": [], "metadatas": []}

        deleted = self.store.delete_document("user-1", "doc-1")

        assert deleted == 0

    def test_delete_user_collection(self):
        """Test deleting an entire user collection."""
        result = self.store.delete_user_collection("user-1")

        assert result is True
        self.mock_client.delete_collection.assert_called_once_with(
            "user_user-1_documents"
        )

    def test_get_collection_stats(self):
        """Test getting collection statistics."""
        self.mock_collection.count.return_value = 42

        stats = self.store.get_collection_stats("user-1")

        assert stats["total_chunks"] == 42
        assert stats["user_id"] == "user-1"

    def test_normalize_score_identical(self):
        """Test score normalization for identical vectors."""
        score = VectorStore._normalize_score(0.0)
        assert score == 1.0

    def test_normalize_score_opposite(self):
        """Test score normalization for opposite vectors."""
        score = VectorStore._normalize_score(2.0)
        assert score == 0.0

    def test_normalize_score_orthogonal(self):
        """Test score normalization for orthogonal vectors."""
        score = VectorStore._normalize_score(1.0)
        assert score == 0.5

    def test_normalize_score_clamped(self):
        """Test that scores are clamped to [0, 1]."""
        assert VectorStore._normalize_score(-0.5) == 1.0  # Clamped to 1.0
        assert VectorStore._normalize_score(2.5) == 0.0  # Clamped to 0.0

    def test_search_results_sorted_by_score(self):
        """Test that search results are sorted by score descending."""
        self.mock_collection.count.return_value = 5
        self.mock_collection.query.return_value = {
            "ids": [["c1", "c2", "c3"]],
            "documents": [["A", "B", "C"]],
            "metadatas": [
                [
                    {"document_id": "d1"},
                    {"document_id": "d1"},
                    {"document_id": "d1"},
                ]
            ],
            "distances": [[0.8, 0.2, 0.5]],  # c2 is closest
        }

        results = self.store.search(
            user_id="user-1",
            query_embedding=[0.1] * 10,
            top_k=3,
        )

        # Results should be sorted: c2 (score 0.9), c3 (score 0.75), c1 (score 0.6)
        assert results[0].chunk_id == "c2"
        assert results[0].score > results[1].score
        assert results[1].score > results[2].score
