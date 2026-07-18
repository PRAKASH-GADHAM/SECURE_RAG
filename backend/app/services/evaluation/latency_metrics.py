"""Latency metrics calculator.

Implements:
- P50 latency
- P95 latency
- P99 latency
- Average latency
- Maximum latency
"""

from typing import Any

from app.utils.logging import get_logger

logger = get_logger(__name__)


class LatencyMetricsCalculator:
    """Calculates latency statistics."""

    def calculate_percentiles(self, latencies: list[float]) -> dict[str, float]:
        """Calculate latency percentiles.

        Args:
            latencies: List of latency values in ms.

        Returns:
            Dictionary of percentile values.
        """
        if not latencies:
            return {
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "average": 0.0,
                "max": 0.0,
                "min": 0.0,
                "count": 0,
            }

        sorted_latencies = sorted(latencies)
        count = len(sorted_latencies)

        return {
            "p50": round(self._percentile(sorted_latencies, 50), 2),
            "p95": round(self._percentile(sorted_latencies, 95), 2),
            "p99": round(self._percentile(sorted_latencies, 99), 2),
            "average": round(sum(sorted_latencies) / count, 2),
            "max": round(max(sorted_latencies), 2),
            "min": round(min(sorted_latencies), 2),
            "count": count,
        }

    def _percentile(self, sorted_data: list[float], percentile: int) -> float:
        """Calculate percentile.

        Args:
            sorted_data: Sorted data list.
            percentile: Percentile to calculate.

        Returns:
            Percentile value.
        """
        if not sorted_data:
            return 0.0

        index = int(len(sorted_data) * percentile / 100)
        index = min(index, len(sorted_data) - 1)
        return sorted_data[index]

    def compare_latencies(
        self,
        before: list[float],
        after: list[float],
    ) -> dict[str, Any]:
        """Compare two latency sets.

        Args:
            before: Latencies before change.
            after: Latencies after change.

        Returns:
            Comparison metrics.
        """
        before_stats = self.calculate_percentiles(before)
        after_stats = self.calculate_percentiles(after)

        return {
            "before": before_stats,
            "after": after_stats,
            "improvement": {
                "p50": round(before_stats["p50"] - after_stats["p50"], 2),
                "p95": round(before_stats["p95"] - after_stats["p95"], 2),
                "p99": round(before_stats["p99"] - after_stats["p99"], 2),
                "average": round(before_stats["average"] - after_stats["average"], 2),
            },
        }

    def calculate_sla_compliance(
        self,
        latencies: list[float],
        sla_threshold_ms: float,
    ) -> dict[str, Any]:
        """Calculate SLA compliance.

        Args:
            latencies: List of latency values.
            sla_threshold_ms: SLA threshold in ms.

        Returns:
            SLA compliance metrics.
        """
        if not latencies:
            return {
                "total_requests": 0,
                "compliant_requests": 0,
                "compliance_rate": 1.0,
            }

        total = len(latencies)
        compliant = sum(1 for l in latencies if l <= sla_threshold_ms)

        return {
            "total_requests": total,
            "compliant_requests": compliant,
            "compliance_rate": round(compliant / total, 4),
            "threshold_ms": sla_threshold_ms,
        }


# Module-level instance
latency_metrics_calculator = LatencyMetricsCalculator()
