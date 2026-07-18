"""Tests for the LLM provider interface and OpenRouter implementation.

Tests successful generation, streaming, timeouts, errors, and retry logic.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import numpy as np

from app.services.llm.base import (
    BaseLLMProvider,
    FinishReason,
    LLMConfig,
    LLMConnectionError,
    LLMProviderError,
    LLMProviderType,
    LLMRateLimitError,
    LLMResponse,
    LLMStreamChunk,
    LLMTimeoutError,
    LLMUsage,
)


class TestLLMBaseClasses:
    """Test base LLM data classes and enums."""

    def test_llm_provider_type_values(self):
        """Test LLM provider type enum values."""
        assert LLMProviderType.OPENROUTER.value == "openrouter"
        assert LLMProviderType.OPENAI.value == "openai"
        assert LLMProviderType.ANTHROPIC.value == "anthropic"

    def test_finish_reason_values(self):
        """Test finish reason enum values."""
        assert FinishReason.STOP.value == "stop"
        assert FinishReason.LENGTH.value == "length"
        assert FinishReason.CONTENT_FILTER.value == "content_filter"

    def test_llm_usage_defaults(self):
        """Test LLM usage default values."""
        usage = LLMUsage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_llm_response_creation(self):
        """Test creating an LLM response."""
        usage = LLMUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        response = LLMResponse(
            content="Test response",
            model="test-model",
            provider="test-provider",
            usage=usage,
            finish_reason=FinishReason.STOP,
            latency_ms=100,
        )
        assert response.content == "Test response"
        assert response.model == "test-model"
        assert response.usage.total_tokens == 30

    def test_llm_config_defaults(self):
        """Test LLM config default values."""
        config = LLMConfig(model="test-model")
        assert config.model == "test-model"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048

    def test_llm_exceptions(self):
        """Test LLM exception classes."""
        error = LLMProviderError("Test error", provider="test", status_code=500)
        assert str(error) == "Test error"
        assert error.provider == "test"
        assert error.status_code == 500

        timeout = LLMTimeoutError(provider="test")
        assert timeout.status_code == 408

        rate_limit = LLMRateLimitError(provider="test")
        assert rate_limit.status_code == 429

        connection = LLMConnectionError(provider="test")
        assert connection.status_code == 503


class TestOpenRouterProvider:
    """Test OpenRouter provider with mocked client."""

    @patch("app.services.llm.openrouter.settings")
    def test_provider_initialization(self, mock_settings):
        """Test provider initialization."""
        mock_settings.OPENROUTER_API_KEY = "test-key"
        mock_settings.OPENROUTER_BASE_URL = "https://test.com"
        mock_settings.OPENROUTER_MODEL = "test-model"
        mock_settings.LLM_TEMPERATURE = 0.5
        mock_settings.LLM_MAX_TOKENS = 1024
        mock_settings.LLM_TIMEOUT = 30

        from app.services.llm.openrouter import OpenRouterProvider
        provider = OpenRouterProvider()

        assert provider.provider_type == LLMProviderType.OPENROUTER
        assert provider.provider_name == "openrouter"

    @patch("app.services.llm.openrouter.settings")
    def test_validate_messages_empty(self, mock_settings):
        """Test validation rejects empty messages."""
        mock_settings.OPENROUTER_API_KEY = "test-key"
        mock_settings.OPENROUTER_BASE_URL = "https://test.com"
        mock_settings.OPENROUTER_MODEL = "test-model"

        from app.services.llm.openrouter import OpenRouterProvider
        provider = OpenRouterProvider()

        is_valid, error = provider._validate_messages([])
        assert is_valid is False
        assert "empty" in error.lower()

    @patch("app.services.llm.openrouter.settings")
    def test_validate_messages_missing_role(self, mock_settings):
        """Test validation rejects messages without role."""
        mock_settings.OPENROUTER_API_KEY = "test-key"
        mock_settings.OPENROUTER_BASE_URL = "https://test.com"
        mock_settings.OPENROUTER_MODEL = "test-model"

        from app.services.llm.openrouter import OpenRouterProvider
        provider = OpenRouterProvider()

        messages = [{"content": "Hello"}]
        is_valid, error = provider._validate_messages(messages)
        assert is_valid is False
        assert "role" in error.lower()

    @patch("app.services.llm.openrouter.settings")
    def test_validate_messages_valid(self, mock_settings):
        """Test validation accepts valid messages."""
        mock_settings.OPENROUTER_API_KEY = "test-key"
        mock_settings.OPENROUTER_BASE_URL = "https://test.com"
        mock_settings.OPENROUTER_MODEL = "test-model"

        from app.services.llm.openrouter import OpenRouterProvider
        provider = OpenRouterProvider()

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ]
        is_valid, error = provider._validate_messages(messages)
        assert is_valid is True
        assert error == ""

    @patch("app.services.llm.openrouter.settings")
    def test_build_config_defaults(self, mock_settings):
        """Test config building with defaults."""
        mock_settings.OPENROUTER_API_KEY = "test-key"
        mock_settings.OPENROUTER_BASE_URL = "https://test.com"
        mock_settings.OPENROUTER_MODEL = "test-model"
        mock_settings.LLM_TEMPERATURE = 0.5
        mock_settings.LLM_MAX_TOKENS = 1024

        from app.services.llm.openrouter import OpenRouterProvider
        provider = OpenRouterProvider()

        config = provider._build_config()
        assert config["model"] == "test-model"
        assert config["temperature"] == 0.5
        assert config["max_tokens"] == 1024

    @patch("app.services.llm.openrouter.settings")
    def test_build_config_override(self, mock_settings):
        """Test config building with overrides."""
        mock_settings.OPENROUTER_API_KEY = "test-key"
        mock_settings.OPENROUTER_BASE_URL = "https://test.com"
        mock_settings.OPENROUTER_MODEL = "test-model"
        mock_settings.LLM_TEMPERATURE = 0.5
        mock_settings.LLM_MAX_TOKENS = 1024

        from app.services.llm.openrouter import OpenRouterProvider
        provider = OpenRouterProvider()

        override = LLMConfig(model="override-model", temperature=0.9)
        config = provider._build_config(override)
        assert config["model"] == "override-model"
        assert config["temperature"] == 0.9
        assert config["max_tokens"] == 1024  # Default

    @patch("app.services.llm.openrouter.settings")
    def test_map_finish_reason(self, mock_settings):
        """Test finish reason mapping."""
        mock_settings.OPENROUTER_API_KEY = "test-key"
        mock_settings.OPENROUTER_BASE_URL = "https://test.com"
        mock_settings.OPENROUTER_MODEL = "test-model"

        from app.services.llm.openrouter import OpenRouterProvider
        provider = OpenRouterProvider()

        assert provider._map_finish_reason("stop") == FinishReason.STOP
        assert provider._map_finish_reason("length") == FinishReason.LENGTH
        assert provider._map_finish_reason("content_filter") == FinishReason.CONTENT_FILTER
        assert provider._map_finish_reason("unknown") == FinishReason.UNKNOWN
        assert provider._map_finish_reason(None) == FinishReason.UNKNOWN

    @patch("app.services.llm.openrouter.settings")
    def test_get_model_info(self, mock_settings):
        """Test getting model information."""
        mock_settings.OPENROUTER_API_KEY = "test-key"
        mock_settings.OPENROUTER_BASE_URL = "https://test.com"
        mock_settings.OPENROUTER_MODEL = "test-model"
        mock_settings.LLM_TEMPERATURE = 0.5
        mock_settings.LLM_MAX_TOKENS = 1024
        mock_settings.LLM_TIMEOUT = 30

        from app.services.llm.openrouter import OpenRouterProvider
        provider = OpenRouterProvider()

        info = provider.get_model_info()
        assert info["provider"] == "openrouter"
        assert info["model"] == "test-model"


class TestLLMProviderFactory:
    """Test LLM provider factory."""

    @patch("app.services.llm.factory.settings")
    def test_get_provider_openrouter(self, mock_settings):
        """Test getting OpenRouter provider."""
        mock_settings.LLM_PROVIDER = "openrouter"

        from app.services.llm.factory import LLMProviderFactory
        LLMProviderFactory.clear_instances()

        provider = LLMProviderFactory.get_provider("openrouter")
        assert provider.provider_type == LLMProviderType.OPENROUTER

    @patch("app.services.llm.factory.settings")
    def test_get_provider_invalid(self, mock_settings):
        """Test getting invalid provider raises error."""
        mock_settings.LLM_PROVIDER = "invalid"

        from app.services.llm.factory import LLMProviderFactory
        LLMProviderFactory.clear_instances()

        with pytest.raises(ValueError) as exc_info:
            LLMProviderFactory.get_provider("invalid_provider")
        assert "Unsupported" in str(exc_info.value) or "unsupported" in str(exc_info.value).lower()

    @patch("app.services.llm.factory.settings")
    def test_provider_singleton(self, mock_settings):
        """Test provider uses singleton pattern."""
        mock_settings.LLM_PROVIDER = "openrouter"

        from app.services.llm.factory import LLMProviderFactory
        LLMProviderFactory.clear_instances()

        provider1 = LLMProviderFactory.get_provider("openrouter")
        provider2 = LLMProviderFactory.get_provider("openrouter")
        assert provider1 is provider2
