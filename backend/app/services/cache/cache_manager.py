"""Cache manager for orchestrating all cache operations.

Provides unified interface for cache operations with TTL management,
invalidation, and metrics tracking.
"""

import hashlib
import time
from typing import Any, Optional

from app.config import get_settings
from app.services.cache.redis_cache import redis_cache
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class CacheManager:
    """Orchestrates cache operations with metrics tracking."""

    def __init__(self):
        """Initialize cache manager."""
        self._metrics = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }
        logger.info("Cache manager initialized")

    async def get(
        self,
        key: str,
        prefix: str = "",
    ) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key.
            prefix: Key prefix.

        Returns:
            Cached value or None.
        """
        full_key = self._make_key(key, prefix)

        try:
            value = await redis_cache.get(full_key)
            if value is not None:
                self._metrics["hits"] += 1
                return value
            else:
                self._metrics["misses"] += 1
                return None
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Cache get failed: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        prefix: str = "",
    ) -> bool:
        """Set value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time to live in seconds.
            prefix: Key prefix.

        Returns:
            True if successful.
        """
        full_key = self._make_key(key, prefix)
        effective_ttl = ttl or settings.CACHE_DEFAULT_TTL

        try:
            success = await redis_cache.set(full_key, value, effective_ttl)
            if success:
                self._metrics["sets"] += 1
            return success
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Cache set failed: {e}")
            return False

    async def delete(
        self,
        key: str,
        prefix: str = "",
    ) -> bool:
        """Delete key from cache.

        Args:
            key: Cache key.
            prefix: Key prefix.

        Returns:
            True if successful.
        """
        full_key = self._make_key(key, prefix)

        try:
            success = await redis_cache.delete(full_key)
            if success:
                self._metrics["deletes"] += 1
            return success
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Cache delete failed: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern.

        Args:
            pattern: Key pattern.

        Returns:
            Number of keys invalidated.
        """
        try:
            count = await redis_cache.flush_pattern(pattern)
            self._metrics["deletes"] += count
            return count
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Cache invalidate_pattern failed: {e}")
            return 0

    def generate_hash(self, *args: Any) -> str:
        """Generate hash key from arguments.

        Args:
            *args: Arguments to hash.

        Returns:
            Hash string.
        """
        content = ":".join(str(arg) for arg in args)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _make_key(self, key: str, prefix: str) -> str:
        """Make full cache key with prefix.

        Args:
            key: Base key.
            prefix: Key prefix.

        Returns:
            Full cache key.
        """
        if prefix:
            return f"{prefix}:{key}"
        return key

    def get_metrics(self) -> dict[str, Any]:
        """Get cache metrics.

        Returns:
            Metrics dictionary.
        """
        total = self._metrics["hits"] + self._metrics["misses"]
        hit_ratio = self._metrics["hits"] / total if total > 0 else 0.0

        return {
            **self._metrics,
            "total_requests": total,
            "hit_ratio": round(hit_ratio, 4),
            "miss_ratio": round(1 - hit_ratio, 4),
        }

    def reset_metrics(self) -> None:
        """Reset cache metrics."""
        self._metrics = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }


# Module-level instance
cache_manager = CacheManager()
