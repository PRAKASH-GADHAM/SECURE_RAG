"""Response cache for caching LLM responses.

Caches LLM responses to avoid redundant API calls:
- Key: hash(system_prompt + query + context + model)
- TTL: Configurable (default 6 hours)
"""

import json
from typing import Any, Optional

from app.config import get_settings
from app.services.cache.cache_manager import cache_manager
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

CACHE_PREFIX = "response"


class ResponseCache:
    """Cache for LLM responses."""

    def __init__(self):
        """Initialize response cache."""
        self._enabled = getattr(settings, "RESPONSE_CACHE_ENABLED", True)
        self._ttl = getattr(settings, "RESPONSE_CACHE_TTL", 21600)  # 6 hours
        logger.info(
            "Response cache initialized",
            enabled=self._enabled,
            ttl=self._ttl,
        )

    def _make_key(
        self,
        query: str,
        model: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        """Generate cache key for response.

        Args:
            query: User query.
            model: LLM model name.
            system_prompt: Optional system prompt.
            context: Optional context.

        Returns:
            Cache key.
        """
        # Truncate context for key generation to avoid very long keys
        context_truncated = context[:500] if context else ""
        system_truncated = system_prompt[:200] if system_prompt else ""

        return cache_manager.generate_hash(
            system_truncated, query, context_truncated, model
        )

    async def get(
        self,
        query: str,
        model: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Get cached response.

        Args:
            query: User query.
            model: LLM model name.
            system_prompt: Optional system prompt.
            context: Optional context.

        Returns:
            Cached response or None.
        """
        if not self._enabled:
            return None

        key = self._make_key(query, model, system_prompt, context)
        return await cache_manager.get(key, prefix=CACHE_PREFIX)

    async def set(
        self,
        query: str,
        model: str,
        response: dict[str, Any],
        system_prompt: Optional[str] = None,
        context: Optional[str] = None,
    ) -> bool:
        """Cache response.

        Args:
            query: User query.
            model: LLM model name.
            response: Response to cache.
            system_prompt: Optional system prompt.
            context: Optional context.

        Returns:
            True if successful.
        """
        if not self._enabled:
            return False

        key = self._make_key(query, model, system_prompt, context)
        return await cache_manager.set(
            key, response, ttl=self._ttl, prefix=CACHE_PREFIX
        )

    async def invalidate(self, query: str, model: str) -> bool:
        """Invalidate cached response.

        Args:
            query: User query.
            model: LLM model name.

        Returns:
            True if successful.
        """
        key = self._make_key(query, model)
        return await cache_manager.delete(key, prefix=CACHE_PREFIX)

    async def invalidate_all(self) -> int:
        """Invalidate all cached responses.

        Returns:
            Number of entries invalidated.
        """
        return await cache_manager.invalidate_pattern(f"{CACHE_PREFIX}:*")

    def is_enabled(self) -> bool:
        """Check if response cache is enabled.

        Returns:
            True if enabled.
        """
        return self._enabled


# Module-level instance
response_cache = ResponseCache()
