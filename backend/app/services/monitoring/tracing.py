"""Request tracing for distributed tracing.

Provides request tracing capabilities for tracking requests
across multiple services and components.
"""

import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Optional

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Context variable for current trace
current_trace: ContextVar[Optional["Trace"]] = ContextVar("current_trace", default=None)


@dataclass
class TraceSpan:
    """A single trace span."""

    span_id: str
    name: str
    start_time: float
    end_time: Optional[float] = None
    parent_span_id: Optional[str] = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds.

        Returns:
            Duration in ms.
        """
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    @property
    def is_completed(self) -> bool:
        """Check if span is completed.

        Returns:
            True if completed.
        """
        return self.end_time is not None

    def add_event(self, name: str, attributes: Optional[dict[str, Any]] = None) -> None:
        """Add an event to the span.

        Args:
            name: Event name.
            attributes: Event attributes.
        """
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute.

        Args:
            key: Attribute key.
            value: Attribute value.
        """
        self.attributes[key] = value

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Span dictionary.
        """
        return {
            "span_id": self.span_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "parent_span_id": self.parent_span_id,
            "attributes": self.attributes,
            "events": self.events,
        }


@dataclass
class Trace:
    """A complete trace with multiple spans."""

    trace_id: str
    name: str
    start_time: float
    end_time: Optional[float] = None
    spans: list[TraceSpan] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """Get trace duration in milliseconds.

        Returns:
            Duration in ms.
        """
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    @property
    def span_count(self) -> int:
        """Get number of spans.

        Returns:
            Span count.
        """
        return len(self.spans)

    def start_span(self, name: str, parent_span_id: Optional[str] = None) -> TraceSpan:
        """Start a new span.

        Args:
            name: Span name.
            parent_span_id: Optional parent span ID.

        Returns:
            New trace span.
        """
        span = TraceSpan(
            span_id=str(uuid.uuid4())[:8],
            name=name,
            start_time=time.time(),
            parent_span_id=parent_span_id,
        )
        self.spans.append(span)
        return span

    def end(self) -> None:
        """End the trace."""
        self.end_time = time.time()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Trace dictionary.
        """
        return {
            "trace_id": self.trace_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "span_count": self.span_count,
            "spans": [span.to_dict() for span in self.spans],
            "attributes": self.attributes,
        }


class Tracer:
    """Distributed tracer for request tracking."""

    def __init__(self):
        """Initialize tracer."""
        self._enabled = getattr(settings, "TRACING_ENABLED", True)
        self._traces: list[Trace] = []
        self._max_traces = 1000
        logger.info("Tracer initialized", enabled=self._enabled)

    def start_trace(self, name: str, trace_id: Optional[str] = None) -> Trace:
        """Start a new trace.

        Args:
            name: Trace name.
            trace_id: Optional trace ID.

        Returns:
            New trace.
        """
        if not self._enabled:
            return Trace(
                trace_id=trace_id or str(uuid.uuid4()),
                name=name,
                start_time=time.time(),
            )

        trace = Trace(
            trace_id=trace_id or str(uuid.uuid4()),
            name=name,
            start_time=time.time(),
        )

        self._traces.append(trace)
        if len(self._traces) > self._max_traces:
            self._traces = self._traces[-self._max_traces:]

        current_trace.set(trace)
        return trace

    def get_current_trace(self) -> Optional[Trace]:
        """Get current trace.

        Returns:
            Current trace or None.
        """
        return current_trace.get()

    def start_span(self, name: str) -> Optional[TraceSpan]:
        """Start a span in current trace.

        Args:
            name: Span name.

        Returns:
            New span or None.
        """
        trace = self.get_current_trace()
        if trace:
            return trace.start_span(name)
        return None

    def end_span(self, span: TraceSpan) -> None:
        """End a span.

        Args:
            span: Span to end.
        """
        span.end_time = time.time()

    def end_trace(self) -> None:
        """End current trace."""
        trace = self.get_current_trace()
        if trace:
            trace.end()

    def get_recent_traces(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent traces.

        Args:
            limit: Maximum number of traces.

        Returns:
            List of trace dictionaries.
        """
        return [trace.to_dict() for trace in self._traces[-limit:]]

    def get_trace_by_id(self, trace_id: str) -> Optional[dict[str, Any]]:
        """Get trace by ID.

        Args:
            trace_id: Trace ID.

        Returns:
            Trace dictionary or None.
        """
        for trace in self._traces:
            if trace.trace_id == trace_id:
                return trace.to_dict()
        return None

    def clear(self) -> None:
        """Clear all traces."""
        self._traces.clear()


# Module-level instance
tracer = Tracer()
