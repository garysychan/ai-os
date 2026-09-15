"""Pure functions for immutable Controller sessions."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from ai_os.agents import AgentRole, ExecutionResult
from ai_os.tasks import Task
from ai_os.workflow import TransitionEvent

from .errors import ControllerValidationError
from .models import (
    ControllerEventType,
    ControllerOutcome,
    ControllerSession,
    ControllerStage,
)
from .trace import make_trace_event


def create_session(
    task: Task,
    objective: str,
    *,
    started_at: datetime,
    max_fix_attempts: int,
    approval_evidence: tuple[str, ...] = (),
) -> ControllerSession:
    if not objective.strip():
        raise ControllerValidationError("session objective must not be empty")
    if started_at.tzinfo is None or started_at.utcoffset() is None:
        raise ControllerValidationError("session timestamp must be timezone-aware")
    if max_fix_attempts < 0:
        raise ControllerValidationError("max fix attempts must not be negative")
    session_id = str(
        uuid5(NAMESPACE_URL, f"{task.task_id}|{objective.strip()}|{started_at.isoformat()}")
    )
    event = make_trace_event(
        sequence=1,
        session_id=session_id,
        task_id=task.task_id,
        event_type=ControllerEventType.SESSION_STARTED,
        stage=ControllerStage.CREATED,
        actor=AgentRole.CONTROLLER,
        timestamp=started_at,
        reason="Controller session created",
        evidence=approval_evidence,
    )
    return ControllerSession(
        session_id=session_id,
        task_id=task.task_id,
        objective=objective.strip(),
        stage=ControllerStage.CREATED,
        task_status=task.status,
        started_at=started_at,
        updated_at=started_at,
        max_fix_attempts=max_fix_attempts,
        approval_evidence=approval_evidence,
        events=(event,),
    )


def append_event(
    session: ControllerSession,
    *,
    event_type: ControllerEventType,
    stage: ControllerStage,
    actor: AgentRole,
    timestamp: datetime,
    reason: str,
    evidence: tuple[str, ...] = (),
) -> ControllerSession:
    event = make_trace_event(
        sequence=len(session.events) + 1,
        session_id=session.session_id,
        task_id=session.task_id,
        event_type=event_type,
        stage=stage,
        actor=actor,
        timestamp=timestamp,
        reason=reason,
        evidence=evidence,
    )
    return replace(session, stage=stage, updated_at=timestamp, events=(*session.events, event))


def record_result(
    session: ControllerSession,
    result: ExecutionResult,
    *,
    stage: ControllerStage,
    timestamp: datetime,
) -> ControllerSession:
    updated = append_event(
        session,
        event_type=ControllerEventType.RESULT_RECORDED,
        stage=stage,
        actor=result.role,
        timestamp=timestamp,
        reason=result.summary,
        evidence=result.handoff.evidence,
    )
    attempts = session.fix_attempts + (1 if stage is ControllerStage.FIXING else 0)
    return replace(updated, results=(*session.results, result), fix_attempts=attempts)


def record_transition(
    session: ControllerSession,
    transition: TransitionEvent,
) -> ControllerSession:
    updated = append_event(
        session,
        event_type=ControllerEventType.TASK_TRANSITIONED,
        stage=session.stage,
        actor=AgentRole.CONTROLLER,
        timestamp=transition.timestamp,
        reason=transition.reason,
        evidence=transition.evidence,
    )
    return replace(
        updated,
        task_status=transition.target,
        transitions=(*session.transitions, transition),
    )


def terminate_session(
    session: ControllerSession,
    outcome: ControllerOutcome,
    *,
    timestamp: datetime,
    reason: str,
    findings: tuple[str, ...] = (),
) -> ControllerSession:
    if session.outcome is not None:
        raise ControllerValidationError("session is already terminal")
    updated = append_event(
        session,
        event_type=ControllerEventType.SESSION_TERMINATED,
        stage=ControllerStage.TERMINAL,
        actor=AgentRole.CONTROLLER,
        timestamp=timestamp,
        reason=reason,
        evidence=findings,
    )
    return replace(updated, outcome=outcome, blocking_findings=findings)
