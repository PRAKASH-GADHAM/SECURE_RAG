"""Retrieval cache for caching search results.

Caches retrieval results to avoid redundant searches:
- Key: hash(query + filters + user_id)
- TTL: Configurable (default 1 hour)
"""

import json
from typing import Any, Optional

from app.config import get_settings
from app.services.cache.cache_manager import cache_manager
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

CACHE_PREFIX = "retrieval"


class RetrievalCache:
    """Cache for retrieval results."""

    def __init__(self):
        """Initialize retrieval cache."""
        self._enabled = getattr(settings, "RETRIEVAL_CACHE_ENABLED", True)
        self._ttl = getattr(settings, "RETRIEVAL_CACHE_TTL", 3600)  # 1 hour
        logger.info(
            "Retrieval cache initialized",
            enabled=self._enabled,
            ttl=self._ttl,
        )

    def _make_key(
        self,
        query: str,
        user_id: str,
        filters: Optional[dict[str, Any]] = None,
    ) -> str:
        """Generate cache key for retrieval.

        Args:
            query: Search query.
            user_id: User ID.
            filters: Optional filters.

        Returns:
            Cache key.
        """
        filter_str = json.dumps(filters, sort_keys=True) if filters else ""
        return cache_manager.generate_hash(query, user_id, filter_str)

    async def get(
        self,
        query: str,
        user_id: str,
        filters: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Get cached retrieval results.

        Args:
            query: Search query.
            user_id: User ID.
            filters: Optional filters.

        Returns:
            Cached results or None.
        """
        if not self._enabled:
            return None

        key = self._make_key(query, user_id, filters)
        return await cache_manager.get(key, prefix=CACHE_PREFIX)

    async def set(
        self,
        query: str,
        user_id: str,
        results: dict[str, Any],
        filters: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Cache retrieval results.

        Args:
            query: Search query.
            user_id: User ID.
            results: Results to cache.
            filters: Optional filters.

        Returns:
            True if successful.
        """
        if not self._enabled:
            return False

        key = self._make_key(query, user_id, filters)
        return await cache_manager.set(
            key, results, ttl=self._ttl, prefix=CACHE_PREFIX
        )

    async def invalidate_user(self, user_id: str) -> int:
        """Invalidate all cached retrievals for a user.

        Args:
            user_id: User ID.

        Returns:
            Number of entries invalidated.
        """
        pattern = f"{CACHE_PREFIX}:*{user_id}*"
        return await cache_manager.invalidate_pattern(pattern)

    async def invalidate_all(self) -> int:
        """Invalidate all cached retrievals.

        Returns:
            Number of entries invalidated.
        """
        return await cache_manager.invalidate_pattern(f"{CACHE_PREFIX}:*")

    def is_enabled(self) -> bool:
        """Check if retrieval cache is enabled.

        Returns:
            True if enabled.
        """
        return self._enabled


# Module-level instance
retrieval_cache = RetrievalCache()
