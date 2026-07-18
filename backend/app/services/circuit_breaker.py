"""Circuit breaker service.

Provides circuit breaker pattern for LLM provider resilience.
Stops sending requests after consecutive failures and automatically
recovers after a timeout.
"""

import time
from enum import Enum
from typing import Optional

from app.utils.logging import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """Circuit breaker for provider resilience.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject requests
    - HALF_OPEN: Testing recovery, allow limited requests

    Transitions:
    - CLOSED → OPEN: After N consecutive failures
    - OPEN → HALF_OPEN: After timeout expires
    - HALF_OPEN → CLOSED: On successful request
    - HALF_OPEN → OPEN: On failed request
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        name: str = "default",
    ):
        """Initialize the circuit breaker.

        Args:
            failure_threshold: Consecutive failures before opening circuit.
            recovery_timeout: Seconds to wait before trying again.
            name: Circuit breaker name for logging.
        """
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._name = name

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_state_change_time = time.time()

        logger.info(
            f"Circuit breaker '{name}' initialized: "
            f"threshold={failure_threshold}, timeout={recovery_timeout}s"
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        if self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._last_failure_time:
                elapsed = time.time() - self._last_failure_time
                if elapsed >= self._recovery_timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    @property
    def success_count(self) -> int:
        """Get current success count."""
        return self._success_count

    def _transition_to(self, new_state: CircuitState):
        """Transition to a new state.

        Args:
            new_state: The state to transition to.
        """
        old_state = self._state
        self._state = new_state
        self._last_state_change_time = time.time()

        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitState.OPEN:
            self._last_failure_time = time.time()

        logger.info(
            f"Circuit breaker '{self._name}' state changed: "
            f"{old_state.value} → {new_state.value}"
        )

    def record_success(self):
        """Record a successful request."""
        if self._state == CircuitState.HALF_OPEN:
            # Recovery successful
            self._transition_to(CircuitState.CLOSED)
        else:
            self._success_count += 1

    def record_failure(self):
        """Record a failed request."""
        self._failure_count += 1

        if self._state == CircuitState.HALF_OPEN:
            # Failed during recovery, go back to OPEN
            self._transition_to(CircuitState.OPEN)
        elif self._failure_count >= self._failure_threshold:
            # Too many failures, open the circuit
            self._transition_to(CircuitState.OPEN)

    def can_execute(self) -> bool:
        """Check if a request can be executed.

        Returns:
            True if the request should be allowed.
        """
        current_state = self.state  # This checks timeout

        if current_state == CircuitState.CLOSED:
            return True
        elif current_state == CircuitState.HALF_OPEN:
            return True  # Allow one test request
        else:
            return False  # OPEN state

    def reset(self):
        """Reset the circuit breaker to closed state."""
        self._transition_to(CircuitState.CLOSED)
        logger.info(f"Circuit breaker '{self._name}' reset")

    def get_stats(self) -> dict:
        """Get circuit breaker statistics.

        Returns:
            Dictionary with circuit breaker stats.
        """
        return {
            "name": self._name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self._failure_threshold,
            "recovery_timeout": self._recovery_timeout,
            "last_failure_time": self._last_failure_time,
            "last_state_change_time": self._last_state_change_time,
        }
