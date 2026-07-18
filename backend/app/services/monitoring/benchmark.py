"""Benchmark framework for evaluating system components.

Provides benchmarking capabilities for:
- Hybrid Retrieval
- Cross Encoder
- LLM Generation
- Guardrails
- Complete Pipeline
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class BenchmarkResult:
    """Result from a benchmark run."""

    name: str
    iterations: int
    total_time_ms: float
    average_time_ms: float
    min_time_ms: float
    max_time_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    success_rate: float
    error_count: int
    metrics: dict[str, Any] = field(default_factory=dict)


class BenchmarkRunner:
    """Runs benchmarks for system components."""

    def __init__(self):
        """Initialize benchmark runner."""
        self._benchmarks: dict[str, BenchmarkResult] = {}
        logger.info("Benchmark runner initialized")

    def run_benchmark(
        self,
        name: str,
        func: Callable,
        iterations: int = 100,
        warmup: int = 10,
        **kwargs,
    ) -> BenchmarkResult:
        """Run a benchmark.

        Args:
            name: Benchmark name.
            func: Function to benchmark.
            iterations: Number of iterations.
            warmup: Number of warmup iterations.
            **kwargs: Additional arguments for function.

        Returns:
            BenchmarkResult.
        """
        logger.info(f"Running benchmark: {name} ({iterations} iterations)")

        # Warmup
        for _ in range(warmup):
            try:
                func(**kwargs)
            except Exception:
                pass

        # Run benchmark
        latencies = []
        errors = 0
        start_time = time.time()

        for _ in range(iterations):
            iter_start = time.time()
            try:
                func(**kwargs)
                iter_end = time.time()
                latencies.append((iter_end - iter_start) * 1000)
            except Exception:
                errors += 1

        total_time = (time.time() - start_time) * 1000

        # Calculate statistics
        if latencies:
            sorted_latencies = sorted(latencies)
            result = BenchmarkResult(
                name=name,
                iterations=iterations,
                total_time_ms=round(total_time, 2),
                average_time_ms=round(sum(latencies) / len(latencies), 2),
                min_time_ms=round(min(latencies), 2),
                max_time_ms=round(max(latencies), 2),
                p50_ms=round(self._percentile(sorted_latencies, 50), 2),
                p95_ms=round(self._percentile(sorted_latencies, 95), 2),
                p99_ms=round(self._percentile(sorted_latencies, 99), 2),
                success_rate=round((iterations - errors) / iterations, 4),
                error_count=errors,
            )
        else:
            result = BenchmarkResult(
                name=name,
                iterations=iterations,
                total_time_ms=round(total_time, 2),
                average_time_ms=0.0,
                min_time_ms=0.0,
                max_time_ms=0.0,
                p50_ms=0.0,
                p95_ms=0.0,
                p99_ms=0.0,
                success_rate=0.0,
                error_count=errors,
            )

        self._benchmarks[name] = result
        logger.info(f"Benchmark completed: {name} - {result.average_time_ms:.2f}ms avg")

        return result

    def run_async_benchmark(
        self,
        name: str,
        func: Callable,
        iterations: int = 100,
        warmup: int = 10,
        **kwargs,
    ) -> BenchmarkResult:
        """Run an async benchmark (stub for future implementation).

        Args:
            name: Benchmark name.
            func: Async function to benchmark.
            iterations: Number of iterations.
            warmup: Number of warmup iterations.
            **kwargs: Additional arguments for function.

        Returns:
            BenchmarkResult.
        """
        # Placeholder for async benchmark
        return self.run_benchmark(name, func, iterations, warmup, **kwargs)

    def get_benchmark(self, name: str) -> Optional[BenchmarkResult]:
        """Get benchmark result by name.

        Args:
            name: Benchmark name.

        Returns:
            BenchmarkResult or None.
        """
        return self._benchmarks.get(name)

    def get_all_benchmarks(self) -> dict[str, dict[str, Any]]:
        """Get all benchmark results.

        Returns:
            Dictionary of all benchmarks.
        """
        results = {}
        for name, result in self._benchmarks.items():
            results[name] = {
                "iterations": result.iterations,
                "total_time_ms": result.total_time_ms,
                "average_time_ms": result.average_time_ms,
                "min_time_ms": result.min_time_ms,
                "max_time_ms": result.max_time_ms,
                "p50_ms": result.p50_ms,
                "p95_ms": result.p95_ms,
                "p99_ms": result.p99_ms,
                "success_rate": result.success_rate,
                "error_count": result.error_count,
                "metrics": result.metrics,
            }
        return results

    def generate_report(self) -> str:
        """Generate benchmark report.

        Returns:
            Formatted benchmark report.
        """
        if not self._benchmarks:
            return "No benchmarks available."

        lines = ["Benchmark Report", "=" * 50]

        for name, result in self._benchmarks.items():
            lines.append(f"\n{name}:")
            lines.append(f"  Iterations: {result.iterations}")
            lines.append(f"  Average: {result.average_time_ms:.2f}ms")
            lines.append(f"  P50: {result.p50_ms:.2f}ms")
            lines.append(f"  P95: {result.p95_ms:.2f}ms")
            lines.append(f"  P99: {result.p99_ms:.2f}ms")
            lines.append(f"  Min: {result.min_time_ms:.2f}ms")
            lines.append(f"  Max: {result.max_time_ms:.2f}ms")
            lines.append(f"  Success Rate: {result.success_rate * 100:.1f}%")

        return "\n".join(lines)

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

    def clear(self) -> None:
        """Clear all benchmarks."""
        self._benchmarks.clear()


# Module-level instance
benchmark_runner = BenchmarkRunner()
