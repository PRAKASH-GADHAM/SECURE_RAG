"""Abstract LLM provider interface.

Defines the contract that all LLM providers must implement.
The RAG service communicates only through this interface,
never directly with specific providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Optional


class LLMProviderType(str, Enum):
    """Supported LLM provider types."""

    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    AZURE = "azure"


class FinishReason(str, Enum):
    """Reason why the model stopped generating."""

    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class LLMUsage:
    """Token usage information from LLM response."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    content: str
    model: str
    provider: str
    usage: LLMUsage
    finish_reason: FinishReason
    latency_ms: int
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: Optional[str] = None


@dataclass
class LLMStreamChunk:
    """A single chunk from streaming LLM response."""

    content: str
    model: str
    provider: str
    finish_reason: Optional[FinishReason] = None
    usage: Optional[LLMUsage] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    model: str
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60
    stream: bool = True
    system_prompt: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM providers must implement this interface.
    The RAG service communicates only through this abstraction.
    """

    @property
    @abstractmethod
    def provider_type(self) -> LLMProviderType:
        """Get the provider type."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        config: Optional[LLMConfig] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> LLMResponse:
        """Generate a completion.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            config: LLM configuration overrides.
            request_id: Optional request ID for tracking.
            user_id: Optional user ID for logging.

        Returns:
            LLMResponse with generated content and metadata.

        Raises:
            LLMProviderError: If generation fails.
            LLMTimeoutError: If request times out.
            LLMRateLimitError: If rate limited.
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        config: Optional[LLMConfig] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Generate a streaming completion.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            config: LLM configuration overrides.
            request_id: Optional request ID for tracking.
            user_id: Optional user ID for logging.

        Yields:
            LLMStreamChunk objects as they are generated.

        Raises:
            LLMProviderError: If generation fails.
            LLMTimeoutError: If request times out.
            LLMRateLimitError: If rate limited.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available.

        Returns:
            True if the provider is healthy.
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """Get information about the configured model.

        Returns:
            Dictionary with model information.
        """
        pass


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""

    def __init__(self, message: str, provider: str = "", status_code: int = 0):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code


class LLMTimeoutError(LLMProviderError):
    """Exception for LLM timeout errors."""

    def __init__(self, message: str = "LLM request timed out", provider: str = ""):
        super().__init__(message, provider, status_code=408)


class LLMRateLimitError(LLMProviderError):
    """Exception for LLM rate limit errors."""

    def __init__(self, message: str = "Rate limited by LLM provider", provider: str = ""):
        super().__init__(message, provider, status_code=429)


class LLMConnectionError(LLMProviderError):
    """Exception for LLM connection errors."""

    def __init__(self, message: str = "Failed to connect to LLM provider", provider: str = ""):
        super().__init__(message, provider, status_code=503)
