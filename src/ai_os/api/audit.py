"""Bounded, credential-free API security evidence."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

from ai_os.agents import AgentRole, Permission
from ai_os.observability import (
    AuditQueryContext,
    ObservabilityService,
    RuntimeEvent,
    RuntimeEventFilter,
    RuntimeEventSource,
)


@dataclass(frozen=True)
class ApiAuditEvent:
    request_id: str
    timestamp: datetime
    method: str
    route: str
    status_code: int
    outcome: str
    principal_id: str | None = None
    agent_role: str | None = None
    schema_version: int = 1


class ApiAuditRecorder:
    """Bounded API evidence recorder backed by governed runtime observability."""

    def __init__(self, max_events: int, observability: ObservabilityService | None = None) -> None:
        if not 1 <= max_events <= 10_000:
            raise ValueError("API audit capacity must be within 1..10000")
        self._events: deque[ApiAuditEvent] = deque(maxlen=max_events)
        self._observability = observability
        self._lock = Lock()

    def record(
        self,
        *,
        request_id: str,
        method: str,
        route: str,
        status_code: int,
        duration_ms: int,
        principal_id: str | None,
        agent_role: str | None,
    ) -> None:
        outcome = (
            "SUCCESS" if status_code < 400 else "DENIED" if status_code in {401, 403} else "FAILED"
        )
        event = ApiAuditEvent(
            request_id=request_id,
            timestamp=datetime.now(UTC),
            method=method,
            route=route,
            status_code=status_code,
            outcome=outcome,
            principal_id=principal_id,
            agent_role=agent_role,
        )
        if self._observability is not None:
            self._observability.record_api_event(
                request_id=request_id,
                timestamp=event.timestamp,
                method=method,
                route=route,
                status_code=status_code,
                principal_id=principal_id,
                agent_role=AgentRole(agent_role) if agent_role is not None else None,
                duration_ms=duration_ms,
            )
        with self._lock:
            self._events.append(event)

    def list(self, *, limit: int = 100) -> tuple[ApiAuditEvent, ...]:
        capacity = self._events.maxlen
        if capacity is None or not 1 <= limit <= capacity:
            raise ValueError("API audit query exceeds configured bound")
        if self._observability is not None:
            events = self._observability.list(
                context=AuditQueryContext(AgentRole.CONTROLLER, Permission.READ_CONTROL),
                filters=RuntimeEventFilter(source=RuntimeEventSource.API),
                limit=limit,
            )
            return tuple(_api_event(event) for event in events)
        with self._lock:
            return tuple(self._events)[-limit:]


def _api_event(runtime_event: RuntimeEvent) -> ApiAuditEvent:
    correlation = dict(runtime_event.correlation)
    return ApiAuditEvent(
        request_id=runtime_event.trace_id,
        timestamp=runtime_event.timestamp,
        method=correlation.get("method", "UNKNOWN"),
        route=correlation.get("route", "/unmatched"),
        status_code=int(correlation.get("status_code", "500")),
        outcome=correlation.get("outcome", "FAILED"),
        principal_id=runtime_event.session_id,
        agent_role=runtime_event.agent_role,
    )
