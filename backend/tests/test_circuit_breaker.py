"""Tests for circuit breaker pattern.

Covers state transitions, failure counting, recovery, and statistics.
"""

import time
import pytest

from app.services.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreakerInitialState:
    """Tests for initial state of circuit breaker."""

    def test_starts_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        assert cb.state == CircuitState.CLOSED

    def test_initial_failure_count_zero(self):
        cb = CircuitBreaker()
        assert cb.failure_count == 0

    def test_initial_success_count_zero(self):
        cb = CircuitBreaker()
        assert cb.success_count == 0

    def test_can_execute_when_closed(self):
        cb = CircuitBreaker()
        assert cb.can_execute() is True


class TestClosedState:
    """Tests for closed state behavior."""

    def test_stays_closed_after_successes(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_stays_closed_below_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_increments_failure_count(self):
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

    def test_increments_success_count(self):
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_success()
        cb.record_success()
        assert cb.success_count == 2


class TestOpenState:
    """Tests for open state behavior."""

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_blocks_requests_when_open(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
        cb.record_failure()
        cb.record_failure()
        assert cb.can_execute() is False

    def test_records_last_failure_time(self):
        cb = CircuitBreaker(failure_threshold=1)
        before = time.time()
        cb.record_failure()
        after = time.time()
        assert cb.state == CircuitState.OPEN
        assert cb._last_failure_time is not None
        assert before <= cb._last_failure_time <= after


class TestHalfOpenState:
    """Tests for half-open state behavior."""

    def test_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    def test_allows_request_in_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        time.sleep(0.15)
        assert cb.can_execute() is True

    def test_recovery_success_closes_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_recovery_failure_reopens_circuit(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        cb.record_failure()
        assert cb.state == CircuitState.OPEN


class TestReset:
    """Tests for reset functionality."""

    def test_reset_returns_to_closed(self):
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED

    def test_reset_clears_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.reset()
        assert cb.failure_count == 0

    def test_reset_clears_success_count(self):
        cb = CircuitBreaker()
        cb.record_success()
        cb.record_success()
        cb.reset()
        assert cb.success_count == 0


class TestGetStats:
    """Tests for statistics."""

    def test_returns_dict(self):
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30, name="test")
        stats = cb.get_stats()
        assert isinstance(stats, dict)

    def test_includes_name(self):
        cb = CircuitBreaker(name="my-breaker")
        stats = cb.get_stats()
        assert stats["name"] == "my-breaker"

    def test_includes_state(self):
        cb = CircuitBreaker()
        stats = cb.get_stats()
        assert stats["state"] == "closed"

    def test_includes_thresholds(self):
        cb = CircuitBreaker(failure_threshold=10, recovery_timeout=120)
        stats = cb.get_stats()
        assert stats["failure_threshold"] == 10
        assert stats["recovery_timeout"] == 120

    def test_includes_counts(self):
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_failure()
        cb.record_success()
        stats = cb.get_stats()
        assert stats["failure_count"] == 1
        assert stats["success_count"] == 1


class TestCircuitBreakerTransitions:
    """Tests for full state transition lifecycle."""

    def test_closed_to_open_to_half_open_to_closed(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_closed_to_open_to_half_open_back_to_open(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        cb.record_failure()
        assert cb.state == CircuitState.OPEN
