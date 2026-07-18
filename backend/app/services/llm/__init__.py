"""LLM services package.

Provides a provider-agnostic interface for LLM operations.
The RAG service communicates only through the abstract interface,
never directly with specific providers.
"""

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
from app.services.llm.factory import (
    LLMProviderFactory,
    get_llm_provider,
    register_provider,
)

__all__ = [
    # Base classes
    "BaseLLMProvider",
    "LLMProviderType",
    "LLMConfig",
    "LLMResponse",
    "LLMStreamChunk",
    "LLMUsage",
    "FinishReason",
    # Exceptions
    "LLMProviderError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMConnectionError",
    # Factory
    "LLMProviderFactory",
    "get_llm_provider",
    "register_provider",
]
