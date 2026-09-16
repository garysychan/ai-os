"""Immutable execution trace helpers."""

from __future__ import annotations

from datetime import datetime

from .errors import ExecutionValidationError
from .models import ExecutionEvent, ExecutionEventType


def make_event(
    *,
    sequence: int,
    execution_id: str,
    task_id: str,
    event_type: ExecutionEventType,
    timestamp: datetime,
    reason: str,
    step_id: str | None = None,
    attempt: int | None = None,
    evidence: tuple[str, ...] = (),
) -> ExecutionEvent:
    if sequence < 1:
        raise ExecutionValidationError("event sequence must be positive")
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ExecutionValidationError("event timestamp must be timezone-aware")
    if not execution_id.strip() or not task_id.strip() or not reason.strip():
        raise ExecutionValidationError("event identity and reason must not be empty")
    return ExecutionEvent(
        sequence,
        execution_id,
        task_id,
        event_type,
        timestamp,
        reason.strip(),
        step_id,
        attempt,
        evidence,
    )
