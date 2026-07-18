"""Performance profiling for identifying bottlenecks.

Provides profiling capabilities for measuring and analyzing
performance of different system components.
"""

import cProfile
import io
import pstats
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class ProfileResult:
    """Result from profiling a function."""

    function_name: str
    total_time_ms: float
    call_count: int
    average_time_ms: float
    min_time_ms: float
    max_time_ms: float
    calls: list[dict[str, Any]] = field(default_factory=list)


class Profiler:
    """Performance profiler for measuring function execution times."""

    def __init__(self):
        """Initialize profiler."""
        self._enabled = getattr(settings, "PROFILER_ENABLED", False)
        self._profiles: dict[str, list[float]] = {}
        logger.info("Profiler initialized", enabled=self._enabled)

    @contextmanager
    def profile(self, name: str):
        """Profile a code block.

        Args:
            name: Profile name.
        """
        if not self._enabled:
            yield
            return

        start_time = time.time()
        try:
            yield
        finally:
            elapsed_ms = (time.time() - start_time) * 1000
            self._record(name, elapsed_ms)

    def _record(self, name: str, elapsed_ms: float) -> None:
        """Record a profiling sample.

        Args:
            name: Profile name.
            elapsed_ms: Elapsed time in ms.
        """
        if name not in self._profiles:
            self._profiles[name] = []
        self._profiles[name].append(elapsed_ms)

    def get_profile(self, name: str) -> Optional[ProfileResult]:
        """Get profile result for a function.

        Args:
            name: Profile name.

        Returns:
            ProfileResult or None.
        """
        if name not in self._profiles:
            return None

        times = self._profiles[name]
        if not times:
            return None

        return ProfileResult(
            function_name=name,
            total_time_ms=sum(times),
            call_count=len(times),
            average_time_ms=sum(times) / len(times),
            min_time_ms=min(times),
            max_time_ms=max(times),
        )

    def get_all_profiles(self) -> dict[str, dict[str, Any]]:
        """Get all profile results.

        Returns:
            Dictionary of all profiles.
        """
        results = {}
        for name in self._profiles:
            profile = self.get_profile(name)
            if profile:
                results[name] = {
                    "total_time_ms": round(profile.total_time_ms, 2),
                    "call_count": profile.call_count,
                    "average_time_ms": round(profile.average_time_ms, 2),
                    "min_time_ms": round(profile.min_time_ms, 2),
                    "max_time_ms": round(profile.max_time_ms, 2),
                }
        return results

    def reset(self) -> None:
        """Reset all profiles."""
        self._profiles.clear()


class CProfiler:
    """CPU profiler using cProfile."""

    def __init__(self):
        """Initialize CPU profiler."""
        self._enabled = getattr(settings, "CPU_PROFILER_ENABLED", False)
        self._profiler: Optional[cProfile.Profile] = None

    def start(self) -> None:
        """Start CPU profiling."""
        if not self._enabled:
            return

        self._profiler = cProfile.Profile()
        self._profiler.enable()

    def stop(self) -> Optional[dict[str, Any]]:
        """Stop CPU profiling and return results.

        Returns:
            Profiling results or None.
        """
        if not self._enabled or not self._profiler:
            return None

        self._profiler.disable()

        # Get stats
        stream = io.StringIO()
        stats = pstats.Stats(self._profiler, stream=stream)
        stats.sort_stats("cumulative")
        stats.print_stats(10)

        return {
            "output": stream.getvalue(),
            "total_calls": stats.total_calls,
            "total_time": stats.total_tt,
        }

    @contextmanager
    def profile(self, name: str = "cprofile"):
        """Profile a code block with cProfile.

        Args:
            name: Profile name.
        """
        if not self._enabled:
            yield
            return

        self.start()
        try:
            yield
        finally:
            self.stop()


# Module-level instances
profiler = Profiler()
cpu_profiler = CProfiler()
