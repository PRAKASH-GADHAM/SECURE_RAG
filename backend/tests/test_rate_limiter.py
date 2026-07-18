"""Tests for rate limiter service.

Covers key generation, rate limit checking, info retrieval, and reset.
Tests mock Redis to avoid external dependency.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.rate_limit.rate_limiter import RateLimiter


@pytest.fixture
def mock_redis_cache():
    """Mock the redis_cache module used by RateLimiter."""
    with patch("app.services.rate_limit.rate_limiter.redis_cache") as mock:
        mock._client = MagicMock()
        # Pipeline returns a mock that execute() returns results for
        pipe_mock = MagicMock()
        mock._client.pipeline.return_value = pipe_mock

        # Simulate: remove old (0 removed), count=0, add success
        pipe_mock.execute.return_value = [0, 0, 1, True]

        yield mock


@pytest.fixture
def mock_settings():
    """Mock settings for rate limiter."""
    with patch("app.services.rate_limit.rate_limiter.settings") as mock:
        mock.RATE_LIMIT_ENABLED = True
        mock.RATE_LIMIT_REQUESTS = 100
        mock.RATE_LIMIT_WINDOW = 60
        yield mock


@pytest.fixture
def limiter(mock_redis_cache, mock_settings):
    """Create a RateLimiter with mocked dependencies."""
    return RateLimiter()


class TestRateLimiterKeyGeneration:
    """Tests for _make_key."""

    def test_key_without_endpoint(self, limiter):
        key = limiter._make_key("user1")
        assert key == "ratelimit:user1"

    def test_key_with_endpoint(self, limiter):
        key = limiter._make_key("user1", endpoint="/api/v1/chat")
        assert key == "ratelimit:user1:/api/v1/chat"


class TestRateLimiterCheck:
    """Tests for check_rate_limit."""

    @pytest.mark.asyncio
    async def test_allows_when_disabled(self, mock_redis_cache):
        with patch("app.services.rate_limit.rate_limiter.settings") as mock:
            mock.RATE_LIMIT_ENABLED = False
            mock.RATE_LIMIT_REQUESTS = 100
            mock.RATE_LIMIT_WINDOW = 60
            rl = RateLimiter()

        result = await rl.check_rate_limit("user1")
        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_returns_correct_fields(self, limiter):
        result = await limiter.check_rate_limit("user1")
        assert "allowed" in result
        assert "remaining" in result
        assert "limit" in result
        assert "window" in result

    @pytest.mark.asyncio
    async def test_uses_custom_limit_and_window(self, limiter):
        result = await limiter.check_rate_limit("user1", limit=5, window=30)
        assert result["limit"] == 5
        assert result["window"] == 30

    @pytest.mark.asyncio
    async def test_uses_default_limit_and_window(self, limiter):
        result = await limiter.check_rate_limit("user1")
        assert result["limit"] == 100
        assert result["window"] == 60

    @pytest.mark.asyncio
    async def test_redis_failure_fails_open(self, mock_redis_cache, mock_settings):
        mock_redis_cache._client.pipeline.side_effect = Exception("Redis down")
        rl = RateLimiter()
        result = await rl.check_rate_limit("user1")
        assert result["allowed"] is True

    @pytest.mark.asyncio
    async def test_calls_pipeline(self, limiter):
        await limiter.check_rate_limit("user1")
        limiter._redis._client.pipeline.assert_called()


class TestRateLimiterInfo:
    """Tests for get_rate_limit_info."""

    @pytest.mark.asyncio
    async def test_returns_info_fields(self, limiter):
        result = await limiter.get_rate_limit_info("user1")
        assert "limit" in result
        assert "window" in result
        assert "remaining" in result

    @pytest.mark.asyncio
    async def test_disabled_returns_full_remaining(self, mock_redis_cache):
        with patch("app.services.rate_limit.rate_limiter.settings") as mock:
            mock.RATE_LIMIT_ENABLED = False
            mock.RATE_LIMIT_REQUESTS = 100
            mock.RATE_LIMIT_WINDOW = 60
            rl = RateLimiter()

        result = await rl.get_rate_limit_info("user1")
        assert result["remaining"] == 100

    @pytest.mark.asyncio
    async def test_redis_failure_returns_defaults(self, mock_redis_cache, mock_settings):
        mock_redis_cache._client.pipeline.side_effect = Exception("Redis error")
        rl = RateLimiter()
        result = await rl.get_rate_limit_info("user1")
        assert result["remaining"] == 100


class TestRateLimiterReset:
    """Tests for reset_rate_limit."""

    @pytest.mark.asyncio
    async def test_reset_calls_delete(self, limiter):
        mock_delete = AsyncMock(return_value=True)
        limiter._redis.delete = mock_delete
        result = await limiter.reset_rate_limit("user1")
        assert result is True
        mock_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_with_endpoint(self, limiter):
        mock_delete = AsyncMock(return_value=True)
        limiter._redis.delete = mock_delete
        await limiter.reset_rate_limit("user1", endpoint="/api/v1/chat")
        call_key = mock_delete.call_args[0][0]
        assert call_key == "ratelimit:user1:/api/v1/chat"

    @pytest.mark.asyncio
    async def test_reset_failure_returns_false(self, limiter):
        mock_delete = AsyncMock(side_effect=Exception("error"))
        limiter._redis.delete = mock_delete
        result = await limiter.reset_rate_limit("user1")
        assert result is False


class TestRateLimiterEnabled:
    """Tests for is_enabled."""

    def test_enabled(self, limiter):
        assert limiter.is_enabled() is True

    def test_disabled(self, mock_redis_cache):
        with patch("app.services.rate_limit.rate_limiter.settings") as mock:
            mock.RATE_LIMIT_ENABLED = False
            mock.RATE_LIMIT_REQUESTS = 100
            mock.RATE_LIMIT_WINDOW = 60
            rl = RateLimiter()
        assert rl.is_enabled() is False
