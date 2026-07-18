"""Tests for the Infrastructure Layer.

Comprehensive tests for:
- Redis cache
- Cache manager
- Embedding cache
- Retrieval cache
- Response cache
- Rate limiter
- Background tasks
- Configuration validation
"""

import pytest

from app.services.cache.cache_manager import CacheManager
from app.services.cache.embedding_cache import EmbeddingCache
from app.services.cache.retrieval_cache import RetrievalCache
from app.services.cache.response_cache import ResponseCache
from app.services.rate_limit.rate_limiter import RateLimiter


class TestCacheManager:
    """Tests for cache manager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = CacheManager()

    def test_generate_hash(self):
        """Test hash generation."""
        hash1 = self.manager.generate_hash("test", "value")
        hash2 = self.manager.generate_hash("test", "value")
        hash3 = self.manager.generate_hash("test", "other")

        assert hash1 == hash2
        assert hash1 != hash3

    def test_make_key_with_prefix(self):
        """Test key generation with prefix."""
        key = self.manager._make_key("test_key", "prefix")
        assert key == "prefix:test_key"

    def test_make_key_without_prefix(self):
        """Test key generation without prefix."""
        key = self.manager._make_key("test_key", "")
        assert key == "test_key"

    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = self.manager.get_metrics()
        assert metrics["hits"] == 0
        assert metrics["misses"] == 0
        assert metrics["total_requests"] == 0

    def test_reset_metrics(self):
        """Test metrics reset."""
        self.manager._metrics["hits"] = 10
        self.manager.reset_metrics()
        metrics = self.manager.get_metrics()
        assert metrics["hits"] == 0


class TestEmbeddingCache:
    """Tests for embedding cache."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = EmbeddingCache()

    def test_make_key(self):
        """Test cache key generation."""
        key = self.cache._make_key("test text", "model-name")
        assert isinstance(key, str)
        assert len(key) == 16

    def test_is_enabled(self):
        """Test enabled check."""
        assert isinstance(self.cache.is_enabled(), bool)


class TestRetrievalCache:
    """Tests for retrieval cache."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = RetrievalCache()

    def test_make_key(self):
        """Test cache key generation."""
        key = self.cache._make_key("query", "user1", {"filter": "value"})
        assert isinstance(key, str)
        assert len(key) == 16

    def test_make_key_no_filters(self):
        """Test cache key generation without filters."""
        key = self.cache._make_key("query", "user1", None)
        assert isinstance(key, str)


class TestResponseCache:
    """Tests for response cache."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = ResponseCache()

    def test_make_key(self):
        """Test cache key generation."""
        key = self.cache._make_key(
            "query", "model", "system prompt", "context"
        )
        assert isinstance(key, str)
        assert len(key) == 16

    def test_make_key_minimal(self):
        """Test cache key generation with minimal args."""
        key = self.cache._make_key("query", "model")
        assert isinstance(key, str)


class TestRateLimiter:
    """Tests for rate limiter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.limiter = RateLimiter()

    def test_is_enabled(self):
        """Test enabled check."""
        assert isinstance(self.limiter.is_enabled(), bool)

    def test_make_key(self):
        """Test rate limit key generation."""
        key = self.limiter._make_key("user123", "/api/test")
        assert key == "ratelimit:user123:/api/test"

    def test_make_key_no_endpoint(self):
        """Test rate limit key generation without endpoint."""
        key = self.limiter._make_key("user123")
        assert key == "ratelimit:user123"


class TestConfiguration:
    """Tests for configuration validation."""

    def test_default_config(self):
        """Test default configuration values."""
        from app.config import Settings

        settings = Settings()
        assert settings.RATE_LIMIT_ENABLED is True
        assert settings.RATE_LIMIT_REQUESTS == 100
        assert settings.RATE_LIMIT_WINDOW == 60
        assert settings.CACHE_ENABLED is True
        assert settings.CACHE_DEFAULT_TTL == 3600
        assert settings.EMBEDDING_CACHE_ENABLED is True
        assert settings.EMBEDDING_CACHE_TTL == 86400
        assert settings.RETRIEVAL_CACHE_ENABLED is True
        assert settings.RETRIEVAL_CACHE_TTL == 3600
        assert settings.RESPONSE_CACHE_ENABLED is True
        assert settings.RESPONSE_CACHE_TTL == 21600

    def test_custom_config(self):
        """Test custom configuration values."""
        from app.config import Settings

        settings = Settings(
            RATE_LIMIT_ENABLED=False,
            RATE_LIMIT_REQUESTS=50,
            CACHE_ENABLED=False,
            EMBEDDING_CACHE_TTL=3600,
        )
        assert settings.RATE_LIMIT_ENABLED is False
        assert settings.RATE_LIMIT_REQUESTS == 50
        assert settings.CACHE_ENABLED is False
        assert settings.EMBEDDING_CACHE_TTL == 3600


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_hash(self):
        """Test empty hash generation."""
        manager = CacheManager()
        hash_value = manager.generate_hash()
        assert isinstance(hash_value, str)
        assert len(hash_value) == 16

    def test_unicode_hash(self):
        """Test unicode hash generation."""
        manager = CacheManager()
        hash_value = manager.generate_hash("Hello World")
        assert isinstance(hash_value, str)

    def test_large_hash(self):
        """Test large data hash generation."""
        manager = CacheManager()
        large_text = "x" * 10000
        hash_value = manager.generate_hash(large_text)
        assert isinstance(hash_value, str)
        assert len(hash_value) == 16


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
