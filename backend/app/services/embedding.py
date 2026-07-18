"""Embedding service.

Handles text embedding using Sentence Transformers with BAAI/bge-m3.
Provides batch embedding for documents and single embedding for queries.
"""

from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Global model instance (lazy loaded)
_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    """Get or initialize the embedding model.

    Returns:
        SentenceTransformer model instance.
    """
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info(f"Embedding model loaded, dimension: {_model.get_sentence_embedding_dimension()}")
    return _model


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(self, model_name: Optional[str] = None):
        """Initialize the embedding service.

        Args:
            model_name: Optional model name override.
        """
        self._model_name = model_name or settings.EMBEDDING_MODEL
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        """Get the embedding model (lazy loaded)."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self._model_name}")
            self._model = SentenceTransformer(self._model_name)
            logger.info(
                f"Model loaded, dimension: {self._model.get_sentence_embedding_dimension()}"
            )
        return self._model

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self.model.get_sentence_embedding_dimension()

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector as list of floats.
        """
        if not text or not text.strip():
            return [0.0] * self.dimension

        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of texts to embed.
            batch_size: Batch size for processing.
            show_progress: Whether to show progress bar.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        # Filter empty texts
        valid_texts = [t if t and t.strip() else " " for t in texts]

        embeddings = self.model.encode(
            valid_texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=True,
        )

        logger.info(f"Embedded {len(texts)} texts, dimension={self.dimension}")
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Generate embedding for a search query.

        Some models benefit from query-specific formatting.
        For bge-m3, we use the same encoding.

        Args:
            query: Search query text.

        Returns:
            Query embedding vector.
        """
        return self.embed_text(query)


# Module-level instance
embedding_service = EmbeddingService()
