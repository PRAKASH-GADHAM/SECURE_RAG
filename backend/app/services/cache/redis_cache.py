"""Redis cache connection and operations.

Provides Redis client with connection pooling, serialization,
and health check capabilities.
"""

import json
import pickle
from typing import Any, Optional

import redis.asyncio as aioredis

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RedisCache:
    """Redis cache client with connection pooling."""

    def __init__(self):
        """Initialize Redis cache."""
        self._client: Optional[aioredis.Redis] = None
        self._connected = False
        logger.info("Redis cache initialized")

    async def connect(self) -> None:
        """Establish Redis connection."""
        if self._client is not None:
            return

        try:
            self._client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,
                max_connections=20,
                retry_on_timeout=True,
            )
            await self._client.ping()
            self._connected = True
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            self._connected = False
            logger.info("Redis disconnected")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None.
        """
        if not self._connected:
            return None

        try:
            value = await self._client.get(key)
            if value:
                return self._deserialize(value)
            return None
        except Exception as e:
            logger.error(f"Redis get failed: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time to live in seconds.

        Returns:
            True if successful.
        """
        if not self._connected:
            return False

        try:
            serialized = self._serialize(value)
            if ttl:
                await self._client.setex(key, ttl, serialized)
            else:
                await self._client.set(key, serialized)
            return True
        except Exception as e:
            logger.error(f"Redis set failed: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache.

        Args:
            key: Cache key.

        Returns:
            True if successful.
        """
        if not self._connected:
            return False

        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete failed: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: Cache key.

        Returns:
            True if key exists.
        """
        if not self._connected:
            return False

        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists failed: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter.

        Args:
            key: Cache key.
            amount: Amount to increment.

        Returns:
            New value or None.
        """
        if not self._connected:
            return None

        try:
            return await self._client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis increment failed: {e}")
            return None

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on key.

        Args:
            key: Cache key.
            ttl: Time to live in seconds.

        Returns:
            True if successful.
        """
        if not self._connected:
            return False

        try:
            return await self._client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis expire failed: {e}")
            return False

    async def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching pattern.

        Args:
            pattern: Key pattern.

        Returns:
            List of matching keys.
        """
        if not self._connected:
            return []

        try:
            keys = await self._client.keys(pattern)
            return [k.decode() if isinstance(k, bytes) else k for k in keys]
        except Exception as e:
            logger.error(f"Redis keys failed: {e}")
            return []

    async def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern.

        Args:
            pattern: Key pattern.

        Returns:
            Number of keys deleted.
        """
        if not self._connected:
            return 0

        try:
            keys = await self.keys(pattern)
            if keys:
                return await self._client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis flush_pattern failed: {e}")
            return 0

    async def health_check(self) -> dict[str, Any]:
        """Check Redis health.

        Returns:
            Health status dictionary.
        """
        if not self._connected:
            return {"status": "disconnected", "latency_ms": 0}

        try:
            import time
            start = time.time()
            await self._client.ping()
            latency = (time.time() - start) * 1000

            info = await self._client.info("memory")
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage.

        Args:
            value: Value to serialize.

        Returns:
            Serialized bytes.
        """
        try:
            return json.dumps(value).encode("utf-8")
        except (TypeError, ValueError):
            return pickle.dumps(value)

    def _deserialize(self, value: bytes) -> Any:
        """Deserialize stored value.

        Args:
            value: Serialized bytes.

        Returns:
            Deserialized value.
        """
        try:
            return json.loads(value.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return pickle.loads(value)

    @property
    def is_connected(self) -> bool:
        """Check if connected to Redis.

        Returns:
            True if connected.
        """
        return self._connected


# Module-level instance
redis_cache = RedisCache()
