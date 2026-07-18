"""LLM provider factory.

Creates and manages LLM provider instances based on configuration.
Uses singleton pattern to ensure only one instance per provider type.
"""

from typing import Optional

from app.config import get_settings
from app.services.llm.base import BaseLLMProvider, LLMProviderType
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Provider class registry
_PROVIDER_CLASSES: dict[LLMProviderType, type] = {}


def register_provider(provider_type: LLMProviderType, provider_class: type):
    """Register a provider class.

    Args:
        provider_type: The provider type enum.
        provider_class: The provider class implementing BaseLLMProvider.
    """
    _PROVIDER_CLASSES[provider_type] = provider_class


def _get_provider_class(provider_type: LLMProviderType) -> Optional[type]:
    """Get provider class by type.

    Args:
        provider_type: The provider type.

    Returns:
        The provider class or None if not registered.
    """
    return _PROVIDER_CLASSES.get(provider_type)


class LLMProviderFactory:
    """Factory for creating and managing LLM providers.

    Uses singleton pattern to ensure only one instance per provider type.
    The active provider is selected from environment variables.
    """

    _instances: dict[str, BaseLLMProvider] = {}

    @classmethod
    def get_provider(
        cls, provider_type: Optional[str] = None
    ) -> BaseLLMProvider:
        """Get or create an LLM provider instance.

        Args:
            provider_type: Optional provider type override.
                          If None, uses LLM_PROVIDER env var.

        Returns:
            LLM provider instance.

        Raises:
            ValueError: If provider type is not supported.
        """
        if provider_type is None:
            provider_type = getattr(settings, "LLM_PROVIDER", "openrouter")

        try:
            ptype = LLMProviderType(provider_type)
        except ValueError:
            raise ValueError(
                f"Unsupported LLM provider: {provider_type}. "
                f"Supported: {[p.value for p in LLMProviderType]}"
            )

        # Check for existing instance (singleton per provider)
        cache_key = ptype.value
        if cache_key in cls._instances:
            return cls._instances[cache_key]

        # Get provider class
        provider_class = _get_provider_class(ptype)
        if provider_class is None:
            raise ValueError(
                f"Provider class not registered for: {ptype.value}"
            )

        # Create new instance
        instance = provider_class()
        cls._instances[cache_key] = instance

        logger.info(f"LLM provider created: {ptype.value}")
        return instance

    @classmethod
    def get_default_provider(cls) -> BaseLLMProvider:
        """Get the default LLM provider.

        Returns:
            Default LLM provider instance.
        """
        return cls.get_provider()

    @classmethod
    def clear_instances(cls):
        """Clear all cached provider instances.

        Useful for testing or configuration changes.
        """
        cls._instances.clear()
        logger.info("LLM provider instances cleared")


# Register providers on module load
def _register_default_providers():
    """Register all built-in providers."""
    from app.services.llm.openrouter import OpenRouterProvider

    register_provider(LLMProviderType.OPENROUTER, OpenRouterProvider)

    # Future providers can be registered here:
    # register_provider(LLMProviderType.OPENAI, OpenAIProvider)
    # register_provider(LLMProviderType.ANTHROPIC, AnthropicProvider)
    # register_provider(LLMProviderType.OLLAMA, OllamaProvider)
    # register_provider(LLMProviderType.GEMINI, GeminiProvider)
    # register_provider(LLMProviderType.AZURE, AzureProvider)

    logger.info("Default LLM providers registered")


_register_default_providers()


def get_llm_provider(provider_type: Optional[str] = None) -> BaseLLMProvider:
    """Convenience function to get an LLM provider.

    Args:
        provider_type: Optional provider type override.

    Returns:
        LLM provider instance.
    """
    return LLMProviderFactory.get_provider(provider_type)
