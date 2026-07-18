"""Core metrics tracking for observability.

Tracks:
- API latency
- Retrieval latency
- Embedding latency
- Reranking latency
- LLM latency
- Guardrail latency
- Cache hit ratio
- Redis latency
- Background task latency
- Document ingestion latency
"""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class LatencyMetrics:
    """Latency metrics with percentile calculations."""

    samples: deque = field(default_factory=lambda: deque(maxlen=10000))

    def record(self, latency_ms: float) -> None:
        """Record a latency sample.

        Args:
            latency_ms: Latency in milliseconds.
        """
        self.samples.append(latency_ms)

    def get_p50(self) -> float:
        """Get 50th percentile latency.

        Returns:
            P50 latency in ms.
        """
        return self._percentile(50)

    def get_p95(self) -> float:
        """Get 95th percentile latency.

        Returns:
            P95 latency in ms.
        """
        return self._percentile(95)

    def get_p99(self) -> float:
        """Get 99th percentile latency.

        Returns:
            P99 latency in ms.
        """
        return self._percentile(99)

    def get_average(self) -> float:
        """Get average latency.

        Returns:
            Average latency in ms.
        """
        if not self.samples:
            return 0.0
        return sum(self.samples) / len(self.samples)

    def get_max(self) -> float:
        """Get maximum latency.

        Returns:
            Maximum latency in ms.
        """
        if not self.samples:
            return 0.0
        return max(self.samples)

    def get_min(self) -> float:
        """Get minimum latency.

        Returns:
            Minimum latency in ms.
        """
        if not self.samples:
            return 0.0
        return min(self.samples)

    def get_count(self) -> int:
        """Get number of samples.

        Returns:
            Sample count.
        """
        return len(self.samples)

    def _percentile(self, percentile: int) -> float:
        """Calculate percentile.

        Args:
            percentile: Percentile to calculate.

        Returns:
            Percentile value.
        """
        if not self.samples:
            return 0.0

        sorted_samples = sorted(self.samples)
        index = int(len(sorted_samples) * percentile / 100)
        index = min(index, len(sorted_samples) - 1)
        return sorted_samples[index]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Metrics dictionary.
        """
        return {
            "p50": round(self.get_p50(), 2),
            "p95": round(self.get_p95(), 2),
            "p99": round(self.get_p99(), 2),
            "average": round(self.get_average(), 2),
            "max": round(self.get_max(), 2),
            "min": round(self.get_min(), 2),
            "count": self.get_count(),
        }


class MetricsCollector:
    """Collects and aggregates system metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self._latency_metrics = {
            "api": LatencyMetrics(),
            "retrieval": LatencyMetrics(),
            "embedding": LatencyMetrics(),
            "reranking": LatencyMetrics(),
            "llm": LatencyMetrics(),
            "guardrail": LatencyMetrics(),
            "redis": LatencyMetrics(),
            "background_task": LatencyMetrics(),
            "document_ingestion": LatencyMetrics(),
        }

        self._counters = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_error": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "documents_processed": 0,
            "embeddings_generated": 0,
            "llm_calls": 0,
            "guardrail_blocks": 0,
        }

        self._gauges = {
            "active_connections": 0,
            "queue_length": 0,
            "worker_count": 0,
        }

        logger.info("Metrics collector initialized")

    def record_latency(self, metric_type: str, latency_ms: float) -> None:
        """Record latency for a metric type.

        Args:
            metric_type: Type of metric.
            latency_ms: Latency in milliseconds.
        """
        if metric_type in self._latency_metrics:
            self._latency_metrics[metric_type].record(latency_ms)

    def increment_counter(self, counter: str, value: int = 1) -> None:
        """Increment a counter.

        Args:
            counter: Counter name.
            value: Value to increment by.
        """
        if counter in self._counters:
            self._counters[counter] += value

    def set_gauge(self, gauge: str, value: float) -> None:
        """Set a gauge value.

        Args:
            gauge: Gauge name.
            value: Gauge value.
        """
        if gauge in self._gauges:
            self._gauges[gauge] = value

    def get_latency_metrics(self, metric_type: str) -> Optional[dict[str, Any]]:
        """Get latency metrics for a type.

        Args:
            metric_type: Type of metric.

        Returns:
            Latency metrics dictionary.
        """
        if metric_type in self._latency_metrics:
            return self._latency_metrics[metric_type].to_dict()
        return None

    def get_all_latency_metrics(self) -> dict[str, dict[str, Any]]:
        """Get all latency metrics.

        Returns:
            Dictionary of all latency metrics.
        """
        return {
            metric_type: metrics.to_dict()
            for metric_type, metrics in self._latency_metrics.items()
        }

    def get_counters(self) -> dict[str, int]:
        """Get all counters.

        Returns:
            Dictionary of counters.
        """
        return dict(self._counters)

    def get_gauges(self) -> dict[str, float]:
        """Get all gauges.

        Returns:
            Dictionary of gauges.
        """
        return dict(self._gauges)

    def get_cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio.

        Returns:
            Cache hit ratio (0.0 to 1.0).
        """
        hits = self._counters.get("cache_hits", 0)
        misses = self._counters.get("cache_misses", 0)
        total = hits + misses

        if total == 0:
            return 0.0

        return hits / total

    def get_all_metrics(self) -> dict[str, Any]:
        """Get all metrics.

        Returns:
            Complete metrics dictionary.
        """
        return {
            "latency": self.get_all_latency_metrics(),
            "counters": self.get_counters(),
            "gauges": self.get_gauges(),
            "cache_hit_ratio": round(self.get_cache_hit_ratio(), 4),
        }

    def reset(self) -> None:
        """Reset all metrics."""
        for metrics in self._latency_metrics.values():
            metrics.samples.clear()

        for counter in self._counters:
            self._counters[counter] = 0

        for gauge in self._gauges:
            self._gauges[gauge] = 0


class TimerContext:
    """Context manager for timing operations."""

    def __init__(self, metrics_collector: MetricsCollector, metric_type: str):
        """Initialize timer context.

        Args:
            metrics_collector: Metrics collector instance.
            metric_type: Type of metric to record.
        """
        self._collector = metrics_collector
        self._metric_type = metric_type
        self._start_time: Optional[float] = None

    def __enter__(self) -> "TimerContext":
        """Enter context manager.

        Returns:
            Self.
        """
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager.

        Args:
            exc_type: Exception type.
            exc_val: Exception value.
            exc_tb: Exception traceback.
        """
        if self._start_time:
            elapsed_ms = (time.time() - self._start_time) * 1000
            self._collector.record_latency(self._metric_type, elapsed_ms)


# Module-level instance
metrics_collector = MetricsCollector()


def timer(metric_type: str) -> TimerContext:
    """Create a timer context for timing operations.

    Args:
        metric_type: Type of metric to record.

    Returns:
        TimerContext instance.
    """
    return TimerContext(metrics_collector, metric_type)
