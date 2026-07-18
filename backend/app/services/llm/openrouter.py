"""OpenRouter LLM provider implementation.

Uses OpenAI-compatible API for OpenRouter integration.
Supports both streaming and non-streaming completions.

Security:
- Never logs prompts, context, API keys, or PII
- Only logs request IDs, latency, provider, model, status, retry count, token usage
"""

import asyncio
import time
import uuid
from typing import Any, AsyncIterator, Optional

import openai

from app.config import get_settings
from app.services.circuit_breaker import CircuitBreaker
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
from app.services.llm_metrics import llm_metrics
from app.services.token_budget import token_budget_manager
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Status codes that should trigger retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter LLM provider using OpenAI-compatible API.

    Supports:
    - Standard completion
    - Streaming completion
    - Exponential backoff retry
    - Timeout handling
    - Request validation
    - Circuit breaker pattern
    - Token budget management
    - Streaming cancellation on client disconnect
    """

    def __init__(self):
        """Initialize the OpenRouter provider."""
        self._client: Optional[openai.AsyncOpenAI] = None
        self._config = {
            "api_key": settings.OPENROUTER_API_KEY,
            "base_url": settings.OPENROUTER_BASE_URL,
            "model": settings.OPENROUTER_MODEL,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": settings.LLM_MAX_TOKENS,
            "timeout": settings.LLM_TIMEOUT,
            "http_referer": settings.OPENROUTER_HTTP_REFERER,
            "x_title": settings.OPENROUTER_X_TITLE,
        }
        self._max_retries = settings.LLM_MAX_RETRIES
        self._initial_retry_delay = 1.0

        # Circuit breaker
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=settings.LLM_CIRCUIT_BREAKER_THRESHOLD,
            recovery_timeout=settings.LLM_CIRCUIT_BREAKER_TIMEOUT,
            name="openrouter",
        )

        # Active streams for cancellation
        self._active_streams: dict[str, Any] = {}

        logger.info(
            f"OpenRouter provider initialized: model={self._config['model']}"
        )

    @property
    def provider_type(self) -> LLMProviderType:
        """Get the provider type."""
        return LLMProviderType.OPENROUTER

    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        return "openrouter"

    @property
    def client(self) -> openai.AsyncOpenAI:
        """Get or create the OpenAI client (lazy loaded)."""
        if self._client is None:
            self._client = openai.AsyncOpenAI(
                api_key=self._config["api_key"],
                base_url=self._config["base_url"],
                timeout=self._config["timeout"],
                default_headers={
                    "HTTP-Referer": self._config["http_referer"],
                    "X-Title": self._config["x_title"],
                },
            )
        return self._client

    def _build_config(
        self, config: Optional[LLMConfig] = None
    ) -> dict[str, Any]:
        """Build final configuration from defaults and overrides.

        Args:
            config: Optional configuration overrides.

        Returns:
            Merged configuration dictionary.
        """
        final_config = {
            "model": self._config["model"],
            "temperature": self._config["temperature"],
            "max_tokens": self._config["max_tokens"],
        }

        if config:
            if config.model:
                final_config["model"] = config.model
            if config.temperature is not None:
                final_config["temperature"] = config.temperature
            if config.max_tokens is not None:
                final_config["max_tokens"] = config.max_tokens

        return final_config

    def _validate_messages(
        self, messages: list[dict[str, str]]
    ) -> tuple[bool, str]:
        """Validate messages before sending to LLM.

        Args:
            messages: List of message dictionaries.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not messages:
            return False, "Messages cannot be empty"

        for i, msg in enumerate(messages):
            if "role" not in msg:
                return False, f"Message {i} missing 'role' field"
            if "content" not in msg:
                return False, f"Message {i} missing 'content' field"
            if msg["role"] not in ("system", "user", "assistant"):
                return False, f"Message {i} has invalid role: {msg['role']}"
            if not msg["content"] or not msg["content"].strip():
                return False, f"Message {i} has empty content"

        # Validate token budget
        total_tokens = 0
        for msg in messages:
            total_tokens += token_budget_manager._token_counter.count_tokens(
                msg.get("content", "")
            )

        if total_tokens > settings.LLM_CONTEXT_WINDOW:
            return (
                False,
                f"Total tokens ({total_tokens}) exceeds context window "
                f"({settings.LLM_CONTEXT_WINDOW})",
            )

        return True, ""

    def _map_finish_reason(
        self, reason: Optional[str]
    ) -> FinishReason:
        """Map OpenAI finish reason to our enum.

        Args:
            reason: OpenAI finish reason string.

        Returns:
            Mapped FinishReason enum value.
        """
        mapping = {
            "stop": FinishReason.STOP,
            "length": FinishReason.LENGTH,
            "content_filter": FinishReason.CONTENT_FILTER,
        }
        return mapping.get(reason, FinishReason.UNKNOWN)

    async def _retry_with_backoff(
        self,
        func,
        request_id: str,
        user_id: Optional[str] = None,
    ) -> Any:
        """Execute function with exponential backoff retry.

        Args:
            func: Async function to execute.
            request_id: Request ID for logging.
            user_id: User ID for logging.

        Returns:
            Result from the function.

        Raises:
            LLMProviderError: If all retries fail.
        """
        last_exception = None
        retry_count = 0

        for attempt in range(self._max_retries):
            try:
                return await func()
            except openai.APITimeoutError:
                last_exception = LLMTimeoutError(
                    provider=self.provider_name
                )
                retry_count = attempt + 1
                llm_metrics.record_request(
                    success=False,
                    latency_ms=0,
                    is_timeout=True,
                    retry_count=retry_count,
                )
                logger.warning(
                    f"LLM timeout: request={request_id}, "
                    f"attempt={attempt + 1}/{self._max_retries}"
                )
            except openai.APIStatusError as e:
                if e.status_code in RETRYABLE_STATUS_CODES:
                    if e.status_code == 429:
                        last_exception = LLMRateLimitError(
                            provider=self.provider_name
                        )
                    else:
                        last_exception = LLMProviderError(
                            message=f"Provider error: {e.status_code}",
                            provider=self.provider_name,
                            status_code=e.status_code,
                        )
                    retry_count = attempt + 1
                    llm_metrics.record_request(
                        success=False,
                        latency_ms=0,
                        retry_count=retry_count,
                    )
                    logger.warning(
                        f"LLM error {e.status_code}: request={request_id}, "
                        f"attempt={attempt + 1}/{self._max_retries}"
                    )
                else:
                    llm_metrics.record_request(success=False, latency_ms=0)
                    raise LLMProviderError(
                        message=f"Provider error: {e.status_code}",
                        provider=self.provider_name,
                        status_code=e.status_code,
                    )
            except openai.APIConnectionError:
                last_exception = LLMConnectionError(
                    provider=self.provider_name
                )
                retry_count = attempt + 1
                llm_metrics.record_request(
                    success=False,
                    latency_ms=0,
                    retry_count=retry_count,
                )
                logger.warning(
                    f"LLM connection error: request={request_id}, "
                    f"attempt={attempt + 1}/{self._max_retries}"
                )

            # Exponential backoff
            if attempt < self._max_retries - 1:
                delay = self._initial_retry_delay * (2 ** attempt)
                await asyncio.sleep(delay)

        logger.error(
            f"LLM failed after {retry_count} retries: request={request_id}"
        )
        self._circuit_breaker.record_failure()
        raise last_exception

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
        """
        request_id = request_id or str(uuid.uuid4())
        start_time = time.time()

        # Check circuit breaker
        if not self._circuit_breaker.can_execute():
            llm_metrics.record_request(success=False, latency_ms=0)
            raise LLMProviderError(
                message="Circuit breaker is open. Provider temporarily unavailable.",
                provider=self.provider_name,
            )

        # Validate messages
        is_valid, error_msg = self._validate_messages(messages)
        if not is_valid:
            llm_metrics.record_request(success=False, latency_ms=0)
            raise LLMProviderError(
                message=f"Invalid request: {error_msg}",
                provider=self.provider_name,
            )

        final_config = self._build_config(config)

        # Log only safe metadata (no prompts or content)
        logger.info(
            f"LLM generate: request={request_id}, "
            f"model={final_config['model']}"
        )

        async def _make_request():
            return await self.client.chat.completions.create(
                model=final_config["model"],
                messages=messages,
                temperature=final_config["temperature"],
                max_tokens=final_config["max_tokens"],
                stream=False,
            )

        try:
            response = await self._retry_with_backoff(
                _make_request, request_id, user_id
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Parse response
            content = response.choices[0].message.content or ""
            finish_reason = self._map_finish_reason(
                response.choices[0].finish_reason
            )

            usage = LLMUsage()
            if response.usage:
                usage = LLMUsage(
                    prompt_tokens=response.usage.prompt_tokens or 0,
                    completion_tokens=response.usage.completion_tokens or 0,
                    total_tokens=response.usage.total_tokens or 0,
                )

            # Record success
            self._circuit_breaker.record_success()
            llm_metrics.record_request(
                success=True,
                latency_ms=latency_ms,
                tokens_used=usage.total_tokens,
            )

            llm_response = LLMResponse(
                content=content,
                model=response.model or final_config["model"],
                provider=self.provider_name,
                usage=usage,
                finish_reason=finish_reason,
                latency_ms=latency_ms,
                metadata={
                    "request_id": request_id,
                },
                request_id=request_id,
            )

            # Log only safe metadata (no content)
            logger.info(
                f"LLM generate completed: request={request_id}, "
                f"tokens={usage.total_tokens}, latency={latency_ms}ms"
            )

            return llm_response

        except (LLMProviderError, LLMTimeoutError, LLMRateLimitError):
            raise
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            self._circuit_breaker.record_failure()
            llm_metrics.record_request(success=False, latency_ms=latency_ms)
            # Log only error type, not the full error which might contain sensitive data
            logger.error(
                f"LLM generate failed: request={request_id}, "
                f"type={type(e).__name__}, latency={latency_ms}ms"
            )
            raise LLMProviderError(
                message=f"Generation failed: {type(e).__name__}",
                provider=self.provider_name,
            )

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        config: Optional[LLMConfig] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Generate a streaming completion.

        Supports cancellation when client disconnects.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            config: LLM configuration overrides.
            request_id: Optional request ID for tracking.
            user_id: Optional user ID for logging.

        Yields:
            LLMStreamChunk objects as they are generated.
        """
        request_id = request_id or str(uuid.uuid4())
        start_time = time.time()

        # Check circuit breaker
        if not self._circuit_breaker.can_execute():
            llm_metrics.record_request(success=False, latency_ms=0)
            raise LLMProviderError(
                message="Circuit breaker is open. Provider temporarily unavailable.",
                provider=self.provider_name,
            )

        # Validate messages
        is_valid, error_msg = self._validate_messages(messages)
        if not is_valid:
            llm_metrics.record_request(success=False, latency_ms=0)
            raise LLMProviderError(
                message=f"Invalid request: {error_msg}",
                provider=self.provider_name,
            )

        final_config = self._build_config(config)

        logger.info(
            f"LLM stream start: request={request_id}, "
            f"model={final_config['model']}"
        )

        stream = None
        try:
            stream = await self.client.chat.completions.create(
                model=final_config["model"],
                messages=messages,
                temperature=final_config["temperature"],
                max_tokens=final_config["max_tokens"],
                stream=True,
            )

            # Register stream for cancellation
            self._active_streams[request_id] = stream

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield LLMStreamChunk(
                        content=chunk.choices[0].delta.content,
                        model=chunk.model or final_config["model"],
                        provider=self.provider_name,
                        metadata={
                            "request_id": request_id,
                        },
                    )

                # Final chunk with usage info
                if chunk.choices and chunk.choices[0].finish_reason:
                    latency_ms = int((time.time() - start_time) * 1000)
                    usage = None
                    if hasattr(chunk, "usage") and chunk.usage:
                        usage = LLMUsage(
                            prompt_tokens=chunk.usage.prompt_tokens or 0,
                            completion_tokens=chunk.usage.completion_tokens or 0,
                            total_tokens=chunk.usage.total_tokens or 0,
                        )

                    yield LLMStreamChunk(
                        content="",
                        model=chunk.model or final_config["model"],
                        provider=self.provider_name,
                        finish_reason=self._map_finish_reason(
                            chunk.choices[0].finish_reason
                        ),
                        usage=usage,
                        metadata={
                            "request_id": request_id,
                            "latency_ms": latency_ms,
                        },
                    )

            # Record success
            self._circuit_breaker.record_success()
            llm_metrics.record_streaming_request(
                success=True,
                latency_ms=int((time.time() - start_time) * 1000),
            )

            logger.info(
                f"LLM stream completed: request={request_id}"
            )

        except openai.APITimeoutError:
            llm_metrics.record_request(
                success=False, latency_ms=0, is_timeout=True
            )
            logger.warning(
                f"LLM stream timeout: request={request_id}"
            )
            raise LLMTimeoutError(provider=self.provider_name)
        except openai.APIStatusError as e:
            llm_metrics.record_request(success=False, latency_ms=0)
            logger.error(
                f"LLM stream error {e.status_code}: request={request_id}"
            )
            if e.status_code == 429:
                raise LLMRateLimitError(provider=self.provider_name)
            raise LLMProviderError(
                message=f"Stream error: {e.status_code}",
                provider=self.provider_name,
                status_code=e.status_code,
            )
        except (LLMProviderError, LLMTimeoutError, LLMRateLimitError):
            raise
        except asyncio.CancelledError:
            # Client disconnected, cancel upstream request
            logger.info(
                f"LLM stream cancelled (client disconnect): request={request_id}"
            )
            raise
        except Exception as e:
            llm_metrics.record_request(success=False, latency_ms=0)
            logger.error(
                f"LLM stream failed: request={request_id}, "
                f"type={type(e).__name__}"
            )
            raise LLMProviderError(
                message=f"Stream failed: {type(e).__name__}",
                provider=self.provider_name,
            )
        finally:
            # Clean up stream registration
            self._active_streams.pop(request_id, None)

    async def cancel_stream(self, request_id: str) -> bool:
        """Cancel an active stream.

        Args:
            request_id: Request ID of the stream to cancel.

        Returns:
            True if stream was found and cancelled.
        """
        stream = self._active_streams.get(request_id)
        if stream:
            try:
                await stream.close()
                self._active_streams.pop(request_id, None)
                logger.info(f"Stream cancelled: request={request_id}")
                return True
            except Exception as e:
                logger.warning(f"Failed to cancel stream: {e}")
                return False
        return False

    async def health_check(self) -> dict[str, Any]:
        """Check if OpenRouter is available.

        Returns:
            Dictionary with health check results.
        """
        start_time = time.time()

        try:
            # Simple request to check connectivity
            await self.client.models.list()
            latency_ms = int((time.time() - start_time) * 1000)

            return {
                "provider": self.provider_name,
                "model": self._config["model"],
                "reachable": True,
                "latency_ms": latency_ms,
                "status": "healthy",
                "circuit_breaker": self._circuit_breaker.get_stats(),
            }
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return {
                "provider": self.provider_name,
                "model": self._config["model"],
                "reachable": False,
                "latency_ms": latency_ms,
                "status": "unhealthy",
                "error": type(e).__name__,
                "circuit_breaker": self._circuit_breaker.get_stats(),
            }

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the configured model.

        Returns:
            Dictionary with model information.
        """
        return {
            "provider": self.provider_name,
            "model": self._config["model"],
            "base_url": self._config["base_url"],
            "temperature": self._config["temperature"],
            "max_tokens": self._config["max_tokens"],
            "timeout": self._config["timeout"],
        }

    def get_circuit_breaker_stats(self) -> dict:
        """Get circuit breaker statistics.

        Returns:
            Dictionary with circuit breaker stats.
        """
        return self._circuit_breaker.get_stats()
