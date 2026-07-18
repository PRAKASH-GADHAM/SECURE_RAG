"""Dashboard utilities for metrics visualization.

Provides utilities for formatting and presenting metrics
in a dashboard-friendly format.
"""

from typing import Any

from app.services.monitoring.metrics import metrics_collector
from app.services.monitoring.benchmark import benchmark_runner
from app.utils.logging import get_logger

logger = get_logger(__name__)


class Dashboard:
    """Dashboard utilities for metrics presentation."""

    def __init__(self):
        """Initialize dashboard."""
        logger.info("Dashboard initialized")

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get metrics summary for dashboard.

        Returns:
            Metrics summary dictionary.
        """
        metrics = metrics_collector.get_all_metrics()

        return {
            "timestamp": self._get_timestamp(),
            "metrics": metrics,
            "summary": self._generate_summary(metrics),
        }

    def get_latency_dashboard(self) -> dict[str, Any]:
        """Get latency metrics for dashboard.

        Returns:
            Latency dashboard data.
        """
        latency_metrics = metrics_collector.get_all_latency_metrics()

        return {
            "timestamp": self._get_timestamp(),
            "latency": latency_metrics,
            "alerts": self._check_latency_alerts(latency_metrics),
        }

    def get_performance_dashboard(self) -> dict[str, Any]:
        """Get performance metrics for dashboard.

        Returns:
            Performance dashboard data.
        """
        metrics = metrics_collector.get_all_metrics()

        return {
            "timestamp": self._get_timestamp(),
            "counters": metrics.get("counters", {}),
            "gauges": metrics.get("gauges", {}),
            "cache_hit_ratio": metrics.get("cache_hit_ratio", 0.0),
        }

    def get_benchmark_dashboard(self) -> dict[str, Any]:
        """Get benchmark results for dashboard.

        Returns:
            Benchmark dashboard data.
        """
        benchmarks = benchmark_runner.get_all_benchmarks()

        return {
            "timestamp": self._get_timestamp(),
            "benchmarks": benchmarks,
            "report": benchmark_runner.generate_report(),
        }

    def _generate_summary(self, metrics: dict[str, Any]) -> dict[str, str]:
        """Generate human-readable summary.

        Args:
            metrics: Metrics dictionary.

        Returns:
            Summary dictionary.
        """
        summary = {}

        # Cache hit ratio
        cache_ratio = metrics.get("cache_hit_ratio", 0.0)
        if cache_ratio >= 0.8:
            summary["cache"] = "Excellent"
        elif cache_ratio >= 0.5:
            summary["cache"] = "Good"
        else:
            summary["cache"] = "Needs Improvement"

        # Latency summary
        latency = metrics.get("latency", {})
        api_latency = latency.get("api", {})
        if api_latency:
            p95 = api_latency.get("p95", 0)
            if p95 <= 100:
                summary["api_latency"] = "Excellent"
            elif p95 <= 500:
                summary["api_latency"] = "Good"
            else:
                summary["api_latency"] = "Slow"

        return summary

    def _check_latency_alerts(
        self, latency_metrics: dict[str, dict[str, float]]
    ) -> list[dict[str, Any]]:
        """Check for latency alerts.

        Args:
            latency_metrics: Latency metrics.

        Returns:
            List of alerts.
        """
        alerts = []

        for component, metrics in latency_metrics.items():
            p95 = metrics.get("p95", 0)
            if p95 > 1000:  # Alert if P95 > 1 second
                alerts.append({
                    "component": component,
                    "level": "warning",
                    "message": f"{component} P95 latency ({p95:.0f}ms) exceeds 1000ms",
                })

        return alerts

    def _get_timestamp(self) -> str:
        """Get current timestamp.

        Returns:
            ISO timestamp string.
        """
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()


# Module-level instance
dashboard = Dashboard()
