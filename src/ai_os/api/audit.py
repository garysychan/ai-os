"""Bounded, credential-free API security evidence."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock


@dataclass(frozen=True)
class ApiAuditEvent:
    request_id: str
    timestamp: datetime
    method: str
    route: str
    status_code: int
    outcome: str
    agent_role: str | None = None
    schema_version: int = 1


class ApiAuditRecorder:
    """Bounded process-local evidence recorder with no request payload access."""

    def __init__(self, max_events: int) -> None:
        if not 1 <= max_events <= 10_000:
            raise ValueError("API audit capacity must be within 1..10000")
        self._events: deque[ApiAuditEvent] = deque(maxlen=max_events)
        self._lock = Lock()

    def record(
        self,
        *,
        request_id: str,
        method: str,
        route: str,
        status_code: int,
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
            agent_role=agent_role,
        )
        with self._lock:
            self._events.append(event)

    def list(self, *, limit: int = 100) -> tuple[ApiAuditEvent, ...]:
        capacity = self._events.maxlen
        if capacity is None or not 1 <= limit <= capacity:
            raise ValueError("API audit query exceeds configured bound")
        with self._lock:
            return tuple(self._events)[-limit:]
