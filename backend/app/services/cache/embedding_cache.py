"""Embedding cache for caching vector embeddings.

Caches embeddings to avoid recomputation:
- Key: hash(text + embedding_model)
- TTL: Configurable (default 24 hours)
"""

from typing import Optional

from app.config import get_settings
from app.services.cache.cache_manager import cache_manager
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

CACHE_PREFIX = "embedding"


class EmbeddingCache:
    """Cache for embedding vectors."""

    def __init__(self):
        """Initialize embedding cache."""
        self._enabled = getattr(settings, "EMBEDDING_CACHE_ENABLED", True)
        self._ttl = getattr(settings, "EMBEDDING_CACHE_TTL", 86400)  # 24 hours
        logger.info(
            "Embedding cache initialized",
            enabled=self._enabled,
            ttl=self._ttl,
        )

    def _make_key(self, text: str, model: str) -> str:
        """Generate cache key for embedding.

        Args:
            text: Input text.
            model: Embedding model name.

        Returns:
            Cache key.
        """
        return cache_manager.generate_hash(text, model)

    async def get(
        self,
        text: str,
        model: str,
    ) -> Optional[list[float]]:
        """Get cached embedding.

        Args:
            text: Input text.
            model: Embedding model name.

        Returns:
            Cached embedding or None.
        """
        if not self._enabled:
            return None

        key = self._make_key(text, model)
        return await cache_manager.get(key, prefix=CACHE_PREFIX)

    async def set(
        self,
        text: str,
        model: str,
        embedding: list[float],
    ) -> bool:
        """Cache embedding.

        Args:
            text: Input text.
            model: Embedding model name.
            embedding: Embedding vector.

        Returns:
            True if successful.
        """
        if not self._enabled:
            return False

        key = self._make_key(text, model)
        return await cache_manager.set(
            key, embedding, ttl=self._ttl, prefix=CACHE_PREFIX
        )

    async def get_batch(
        self,
        texts: list[str],
        model: str,
    ) -> dict[int, list[float]]:
        """Get cached embeddings for batch.

        Args:
            texts: List of input texts.
            model: Embedding model name.

        Returns:
            Dictionary mapping index to embedding.
        """
        if not self._enabled:
            return {}

        results = {}
        for i, text in enumerate(texts):
            embedding = await self.get(text, model)
            if embedding is not None:
                results[i] = embedding

        return results

    async def set_batch(
        self,
        texts: list[str],
        model: str,
        embeddings: list[list[float]],
    ) -> int:
        """Cache embeddings for batch.

        Args:
            texts: List of input texts.
            model: Embedding model name.
            embeddings: List of embedding vectors.

        Returns:
            Number of embeddings cached.
        """
        if not self._enabled:
            return 0

        count = 0
        for text, embedding in zip(texts, embeddings):
            if await self.set(text, model, embedding):
                count += 1

        return count

    async def invalidate(self, text: str, model: str) -> bool:
        """Invalidate cached embedding.

        Args:
            text: Input text.
            model: Embedding model name.

        Returns:
            True if successful.
        """
        key = self._make_key(text, model)
        return await cache_manager.delete(key, prefix=CACHE_PREFIX)

    async def invalidate_all(self) -> int:
        """Invalidate all cached embeddings.

        Returns:
            Number of entries invalidated.
        """
        return await cache_manager.invalidate_pattern(f"{CACHE_PREFIX}:*")

    def is_enabled(self) -> bool:
        """Check if embedding cache is enabled.

        Returns:
            True if enabled.
        """
        return self._enabled


# Module-level instance
embedding_cache = EmbeddingCache()
