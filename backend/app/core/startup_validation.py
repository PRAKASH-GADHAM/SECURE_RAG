"""Configuration validation on startup.

Validates critical configuration values at application startup
to fail fast on invalid configuration.
"""

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""

    pass


def validate_startup_config():
    """Validate critical configuration on startup.

    Checks:
    - API key exists for configured provider
    - Provider name is valid
    - Timeout > 0
    - Max tokens > 0
    - Context window > 0

    Raises:
        ConfigurationError: If any validation fails.
    """
    settings = get_settings()
    errors = []

    # Validate LLM provider
    valid_providers = {"openrouter", "openai", "anthropic", "ollama", "gemini", "azure"}
    if settings.LLM_PROVIDER not in valid_providers:
        errors.append(
            f"Invalid LLM_PROVIDER: '{settings.LLM_PROVIDER}'. "
            f"Must be one of: {', '.join(valid_providers)}"
        )

    # Validate API key for OpenRouter
    if settings.LLM_PROVIDER == "openrouter":
        if not settings.OPENROUTER_API_KEY:
            errors.append(
                "OPENROUTER_API_KEY is required when LLM_PROVIDER is 'openrouter'"
            )

    # Validate timeout
    if settings.LLM_TIMEOUT <= 0:
        errors.append(f"LLM_TIMEOUT must be > 0, got {settings.LLM_TIMEOUT}")

    # Validate max tokens
    if settings.LLM_MAX_TOKENS <= 0:
        errors.append(f"LLM_MAX_TOKENS must be > 0, got {settings.LLM_MAX_TOKENS}")

    # Validate context window
    if settings.LLM_CONTEXT_WINDOW <= 0:
        errors.append(
            f"LLM_CONTEXT_WINDOW must be > 0, got {settings.LLM_CONTEXT_WINDOW}"
        )

    # Validate output reserved tokens
    if settings.LLM_OUTPUT_RESERVED_TOKENS <= 0:
        errors.append(
            f"LLM_OUTPUT_RESERVED_TOKENS must be > 0, "
            f"got {settings.LLM_OUTPUT_RESERVED_TOKENS}"
        )

    # Validate circuit breaker
    if settings.LLM_CIRCUIT_BREAKER_THRESHOLD <= 0:
        errors.append(
            f"LLM_CIRCUIT_BREAKER_THRESHOLD must be > 0, "
            f"got {settings.LLM_CIRCUIT_BREAKER_THRESHOLD}"
        )

    if settings.LLM_CIRCUIT_BREAKER_TIMEOUT <= 0:
        errors.append(
            f"LLM_CIRCUIT_BREAKER_TIMEOUT must be > 0, "
            f"got {settings.LLM_CIRCUIT_BREAKER_TIMEOUT}"
        )

    # Validate context window vs max tokens
    if settings.LLM_CONTEXT_WINDOW <= settings.LLM_MAX_TOKENS:
        errors.append(
            f"LLM_CONTEXT_WINDOW ({settings.LLM_CONTEXT_WINDOW}) must be "
            f"greater than LLM_MAX_TOKENS ({settings.LLM_MAX_TOKENS})"
        )

    # Raise if errors
    if errors:
        error_message = "Configuration validation failed:\n" + "\n".join(
            f"  - {e}" for e in errors
        )
        logger.error(error_message)
        raise ConfigurationError(error_message)

    logger.info("Startup configuration validation passed")
