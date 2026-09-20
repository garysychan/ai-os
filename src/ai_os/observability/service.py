"""Governed service for appending and inspecting runtime evidence."""

from __future__ import annotations

from typing import Protocol

from .models import RuntimeEvent, RuntimeEventFilter
from .validation import sanitize_event


class RuntimeEventRepository(Protocol):
    def append_runtime_event(self, event: RuntimeEvent) -> None: ...

    def get_runtime_event(self, event_id: str) -> RuntimeEvent: ...

    def list_runtime_events(
        self, *, filters: RuntimeEventFilter | None = None, limit: int = 100
    ) -> tuple[RuntimeEvent, ...]: ...


class ObservabilityService:
    """Narrow evidence boundary; it never authorizes or executes runtime work."""

    def __init__(self, repository: RuntimeEventRepository) -> None:
        self.repository = repository

    def record(self, event: RuntimeEvent) -> RuntimeEvent:
        sanitized = sanitize_event(event)
        self.repository.append_runtime_event(sanitized)
        return sanitized

    def get(self, event_id: str) -> RuntimeEvent:
        return self.repository.get_runtime_event(event_id)

    def list(
        self, *, filters: RuntimeEventFilter | None = None, limit: int = 100
    ) -> tuple[RuntimeEvent, ...]:
        return self.repository.list_runtime_events(filters=filters, limit=limit)

    def trace(self, trace_id: str, *, limit: int = 100) -> tuple[RuntimeEvent, ...]:
        return self.list(filters=RuntimeEventFilter(trace_id=trace_id), limit=limit)
