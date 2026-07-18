"""Tests for embedding service.

Tests are designed to run without loading the actual model by using mocks.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.embedding import EmbeddingService


class TestEmbeddingService:
    """Tests for the EmbeddingService with mocked model."""

    def setup_method(self):
        """Set up test fixtures with mocked model."""
        self.service = EmbeddingService(model_name="test-model")
        # Create a mock model
        self.mock_model = MagicMock()
        self.mock_model.get_sentence_embedding_dimension.return_value = 384
        self.service._model = self.mock_model

    def test_embed_text_returns_list(self):
        """Test that embed_text returns a list of floats."""
        import numpy as np
        self.mock_model.encode.return_value = np.array([0.1] * 384)

        result = self.service.embed_text("Hello world")

        assert isinstance(result, list)
        assert len(result) == 384
        self.mock_model.encode.assert_called_once()

    def test_embed_text_empty_returns_zeros(self):
        """Test that empty text returns zero vector."""
        result = self.service.embed_text("")

        assert isinstance(result, list)
        assert len(result) == 384
        assert all(v == 0.0 for v in result)

    def test_embed_text_whitespace_returns_zeros(self):
        """Test that whitespace-only text returns zero vector."""
        result = self.service.embed_text("   ")

        assert isinstance(result, list)
        assert all(v == 0.0 for v in result)

    def test_embed_text_normalizes_embeddings(self):
        """Test that embeddings are normalized."""
        import numpy as np
        self.mock_model.encode.return_value = np.array([0.5] * 384)

        self.service.embed_text("Test text")

        call_kwargs = self.mock_model.encode.call_args
        assert call_kwargs[1].get("normalize_embeddings") is True

    def test_embed_batch_returns_list_of_lists(self):
        """Test that embed_batch returns list of embedding lists."""
        import numpy as np
        self.mock_model.encode.return_value = np.array([[0.1] * 384, [0.2] * 384])

        result = self.service.embed_batch(["Hello", "World"])

        assert isinstance(result, list)
        assert len(result) == 2
        assert len(result[0]) == 384

    def test_embed_batch_empty_returns_empty(self):
        """Test that empty batch returns empty list."""
        result = self.service.embed_batch([])

        assert result == []
        self.mock_model.encode.assert_not_called()

    def test_embed_batch_filters_empty_texts(self):
        """Test that empty texts in batch are replaced with spaces."""
        import numpy as np
        self.mock_model.encode.return_value = np.array([[0.1] * 384])

        self.service.embed_batch(["", "  ", "Real text"])

        call_args = self.mock_model.encode.call_args[0][0]
        assert call_args[0] == " "
        assert call_args[1] == " "
        assert call_args[2] == "Real text"

    def test_embed_query_calls_embed_text(self):
        """Test that embed_query delegates to embed_text."""
        import numpy as np
        self.mock_model.encode.return_value = np.array([0.1] * 384)

        result = self.service.embed_query("Test query")

        assert isinstance(result, list)
        assert len(result) == 384

    def test_dimension_property(self):
        """Test that dimension property returns correct value."""
        assert self.service.dimension == 384

    def test_model_lazy_loading(self):
        """Test that model is only loaded once."""
        service = EmbeddingService(model_name="test-model")
        service._model = self.mock_model

        # Access model multiple times
        _ = service.model
        _ = service.model
        _ = service.model

        # Model should not be recreated
        assert service._model is self.mock_model
