"""Pure helpers for immutable execution sessions."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import NAMESPACE_URL, uuid5

from .errors import ExecutionValidationError
from .models import (
    ExecutionContext,
    ExecutionEventType,
    ExecutionOutcome,
    ExecutionPlan,
    ExecutionSession,
    StepResult,
)
from .trace import make_event


def create_session(
    plan: ExecutionPlan, context: ExecutionContext, started_at: datetime
) -> ExecutionSession:
    if started_at.tzinfo is None or started_at.utcoffset() is None:
        raise ExecutionValidationError("session timestamp must be timezone-aware")
    execution_id = str(
        uuid5(
            NAMESPACE_URL,
            f"{plan.task_id}|{plan.plan_id}|{context.controller_session_id}|{started_at.isoformat()}",
        )
    )
    event = make_event(
        sequence=1,
        execution_id=execution_id,
        task_id=plan.task_id,
        event_type=ExecutionEventType.SESSION_STARTED,
        timestamp=started_at,
        reason="execution session created",
        evidence=context.approval_evidence,
    )
    return ExecutionSession(
        execution_id=execution_id,
        plan_id=plan.plan_id,
        task_id=plan.task_id,
        controller_session_id=context.controller_session_id,
        started_at=started_at,
        updated_at=started_at,
        events=(event,),
    )


def append_event(
    session: ExecutionSession,
    event_type: ExecutionEventType,
    timestamp: datetime,
    reason: str,
    *,
    step_id: str | None = None,
    attempt: int | None = None,
    evidence: tuple[str, ...] = (),
) -> ExecutionSession:
    event = make_event(
        sequence=len(session.events) + 1,
        execution_id=session.execution_id,
        task_id=session.task_id,
        event_type=event_type,
        timestamp=timestamp,
        reason=reason,
        step_id=step_id,
        attempt=attempt,
        evidence=evidence,
    )
    return replace(session, updated_at=timestamp, events=(*session.events, event))


def record_result(
    session: ExecutionSession, result: StepResult, timestamp: datetime
) -> ExecutionSession:
    updated = append_event(
        session,
        ExecutionEventType.STEP_FINISHED,
        timestamp,
        result.summary,
        step_id=result.step_id,
        attempt=result.attempt,
        evidence=result.evidence,
    )
    return replace(updated, results=(*session.results, result))


def finish_session(
    session: ExecutionSession,
    outcome: ExecutionOutcome,
    timestamp: datetime,
    reason: str,
    findings: tuple[str, ...] = (),
) -> ExecutionSession:
    if session.outcome is not None:
        raise ExecutionValidationError("execution session is already terminal")
    updated = append_event(
        session,
        ExecutionEventType.SESSION_FINISHED,
        timestamp,
        reason,
        evidence=findings,
    )
    return replace(updated, outcome=outcome, blocking_findings=findings)
