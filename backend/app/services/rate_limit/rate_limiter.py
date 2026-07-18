"""Rate limiter using sliding window algorithm.

Supports:
- Per-user rate limiting
- Per-IP rate limiting
- Per-endpoint rate limiting
- Configurable through environment variables
"""

import time
from typing import Optional

from app.config import get_settings
from app.services.cache.redis_cache import redis_cache
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RateLimiter:
    """Sliding window rate limiter using Redis."""

    def __init__(self):
        """Initialize rate limiter."""
        self._enabled = getattr(settings, "RATE_LIMIT_ENABLED", True)
        self._default_limit = getattr(settings, "RATE_LIMIT_REQUESTS", 100)
        self._default_window = getattr(settings, "RATE_LIMIT_WINDOW", 60)
        logger.info(
            "Rate limiter initialized",
            enabled=self._enabled,
            default_limit=self._default_limit,
            default_window=self._default_window,
        )

    def _make_key(
        self,
        identifier: str,
        endpoint: Optional[str] = None,
    ) -> str:
        """Generate rate limit key.

        Args:
            identifier: User ID or IP address.
            endpoint: Optional endpoint path.

        Returns:
            Rate limit key.
        """
        if endpoint:
            return f"ratelimit:{identifier}:{endpoint}"
        return f"ratelimit:{identifier}"

    async def check_rate_limit(
        self,
        identifier: str,
        endpoint: Optional[str] = None,
        limit: Optional[int] = None,
        window: Optional[int] = None,
    ) -> dict:
        """Check if request is within rate limit.

        Args:
            identifier: User ID or IP address.
            endpoint: Optional endpoint path.
            limit: Request limit (uses default if not specified).
            window: Time window in seconds (uses default if not specified).

        Returns:
            Dictionary with rate limit info.
        """
        if not self._enabled:
            return {
                "allowed": True,
                "remaining": self._default_limit,
                "limit": self._default_limit,
                "window": self._default_window,
            }

        effective_limit = limit or self._default_limit
        effective_window = window or self._default_window
        key = self._make_key(identifier, endpoint)

        try:
            current_time = time.time()
            window_start = current_time - effective_window

            # Use Redis sorted set for sliding window
            pipe = redis_cache._client.pipeline()

            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current entries
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(current_time): current_time})

            # Set expiry
            pipe.expire(key, effective_window)

            results = await pipe.execute()
            current_count = results[1]

            remaining = max(0, effective_limit - current_count - 1)

            return {
                "allowed": current_count < effective_limit,
                "remaining": remaining,
                "limit": effective_limit,
                "window": effective_window,
                "retry_after": effective_window if current_count >= effective_limit else 0,
            }

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if rate limiter fails
            return {
                "allowed": True,
                "remaining": effective_limit,
                "limit": effective_limit,
                "window": effective_window,
            }

    async def get_rate_limit_info(
        self,
        identifier: str,
        endpoint: Optional[str] = None,
    ) -> dict:
        """Get current rate limit info without incrementing.

        Args:
            identifier: User ID or IP address.
            endpoint: Optional endpoint path.

        Returns:
            Rate limit info.
        """
        if not self._enabled:
            return {
                "limit": self._default_limit,
                "window": self._default_window,
                "remaining": self._default_limit,
            }

        key = self._make_key(identifier, endpoint)

        try:
            current_time = time.time()
            window_start = current_time - self._default_window

            # Remove old entries and count
            pipe = redis_cache._client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            results = await pipe.execute()

            current_count = results[1]
            remaining = max(0, self._default_limit - current_count)

            return {
                "limit": self._default_limit,
                "window": self._default_window,
                "remaining": remaining,
                "current": current_count,
            }

        except Exception as e:
            logger.error(f"Rate limit info failed: {e}")
            return {
                "limit": self._default_limit,
                "window": self._default_window,
                "remaining": self._default_limit,
            }

    async def reset_rate_limit(
        self,
        identifier: str,
        endpoint: Optional[str] = None,
    ) -> bool:
        """Reset rate limit for identifier.

        Args:
            identifier: User ID or IP address.
            endpoint: Optional endpoint path.

        Returns:
            True if successful.
        """
        key = self._make_key(identifier, endpoint)

        try:
            await redis_cache.delete(key)
            return True
        except Exception as e:
            logger.error(f"Rate limit reset failed: {e}")
            return False

    def is_enabled(self) -> bool:
        """Check if rate limiter is enabled.

        Returns:
            True if enabled.
        """
        return self._enabled


# Module-level instance
rate_limiter = RateLimiter()
