"""Deterministic immutable trace construction."""

from __future__ import annotations

from datetime import datetime

from ai_os.agents import AgentRole

from .errors import ControllerValidationError
from .models import ControllerEventType, ControllerStage, TraceEvent


def make_trace_event(
    *,
    sequence: int,
    session_id: str,
    task_id: str,
    event_type: ControllerEventType,
    stage: ControllerStage,
    actor: AgentRole,
    timestamp: datetime,
    reason: str,
    evidence: tuple[str, ...] = (),
    correlation: tuple[tuple[str, str], ...] = (),
) -> TraceEvent:
    if sequence < 1:
        raise ControllerValidationError("trace sequence must be positive")
    if not session_id.strip() or not task_id.strip():
        raise ControllerValidationError("trace identity must not be empty")
    if not reason.strip():
        raise ControllerValidationError("trace reason must not be empty")
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ControllerValidationError("trace timestamp must be timezone-aware")
    return TraceEvent(
        sequence=sequence,
        session_id=session_id,
        task_id=task_id,
        event_type=event_type,
        stage=stage,
        actor=actor,
        timestamp=timestamp,
        reason=reason.strip(),
        evidence=evidence,
        correlation=correlation,
    )
