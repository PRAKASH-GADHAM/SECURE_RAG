"""LLM metrics service.

Tracks observability metrics for LLM operations including
request counts, latency, token usage, and error rates.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LLMMetricsSnapshot:
    """Snapshot of LLM metrics."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeout_count: int = 0
    retry_count: int = 0
    total_tokens_used: int = 0
    avg_latency_ms: float = 0.0
    avg_streaming_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0
    success_rate: float = 0.0
    failure_rate: float = 0.0


class LLMMetrics:
    """Tracks LLM observability metrics.

    Metrics tracked:
    - Total requests
    - Success/failure rates
    - Retry count
    - Timeout count
    - Average/min/max latency
    - Streaming latency
    - Token usage
    """

    _instance: Optional["LLMMetrics"] = None

    def __new__(cls) -> "LLMMetrics":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize metrics (only once due to singleton)."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._total_requests = 0
            self._successful_requests = 0
            self._failed_requests = 0
            self._timeout_count = 0
            self._retry_count = 0
            self._total_tokens = 0
            self._latencies: list[int] = []
            self._streaming_latencies: list[int] = []
            logger.info("LLM Metrics initialized")

    def record_request(
        self,
        success: bool,
        latency_ms: int,
        tokens_used: int = 0,
        is_timeout: bool = False,
        retry_count: int = 0,
    ):
        """Record an LLM request.

        Args:
            success: Whether the request succeeded.
            latency_ms: Request latency in milliseconds.
            tokens_used: Total tokens consumed.
            is_timeout: Whether the request timed out.
            retry_count: Number of retries attempted.
        """
        self._total_requests += 1

        if success:
            self._successful_requests += 1
        else:
            self._failed_requests += 1

        if is_timeout:
            self._timeout_count += 1

        self._retry_count += retry_count
        self._total_tokens += tokens_used
        self._latencies.append(latency_ms)

        # Keep only last 1000 latencies for memory efficiency
        if len(self._latencies) > 1000:
            self._latencies = self._latencies[-1000:]

    def record_streaming_request(
        self,
        success: bool,
        latency_ms: int,
        tokens_used: int = 0,
    ):
        """Record a streaming LLM request.

        Args:
            success: Whether the request succeeded.
            latency_ms: Total streaming latency.
            tokens_used: Total tokens consumed.
        """
        self._total_requests += 1

        if success:
            self._successful_requests += 1
        else:
            self._failed_requests += 1

        self._total_tokens += tokens_used
        self._streaming_latencies.append(latency_ms)

        if len(self._streaming_latencies) > 1000:
            self._streaming_latencies = self._streaming_latencies[-1000:]

    def get_metrics(self) -> LLMMetricsSnapshot:
        """Get current metrics snapshot.

        Returns:
            LLMMetricsSnapshot with current metrics.
        """
        avg_latency = (
            sum(self._latencies) / len(self._latencies)
            if self._latencies
            else 0.0
        )
        avg_streaming = (
            sum(self._streaming_latencies) / len(self._streaming_latencies)
            if self._streaming_latencies
            else 0.0
        )

        success_rate = (
            (self._successful_requests / self._total_requests * 100)
            if self._total_requests > 0
            else 0.0
        )
        failure_rate = (
            (self._failed_requests / self._total_requests * 100)
            if self._total_requests > 0
            else 0.0
        )

        return LLMMetricsSnapshot(
            total_requests=self._total_requests,
            successful_requests=self._successful_requests,
            failed_requests=self._failed_requests,
            timeout_count=self._timeout_count,
            retry_count=self._retry_count,
            total_tokens_used=self._total_tokens,
            avg_latency_ms=avg_latency,
            avg_streaming_latency_ms=avg_streaming,
            min_latency_ms=min(self._latencies) if self._latencies else 0,
            max_latency_ms=max(self._latencies) if self._latencies else 0,
            success_rate=success_rate,
            failure_rate=failure_rate,
        )

    def reset(self):
        """Reset all metrics."""
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._timeout_count = 0
        self._retry_count = 0
        self._total_tokens = 0
        self._latencies = []
        self._streaming_latencies = []
        logger.info("LLM Metrics reset")


# Module-level instance
llm_metrics = LLMMetrics()
