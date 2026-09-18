"""Deterministic Workflow Engine over the existing Controller authority boundary."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime

from ai_os.controller import ControllerEngine, ControllerEventType, ControllerOutcome
from ai_os.tasks import Task, TaskStatus

from .errors import WorkflowPolicyError
from .models import (
    WorkflowEvent,
    WorkflowResult,
    WorkflowSession,
    WorkflowStatus,
)
from .policy import WorkflowPolicy
from .registry import WorkflowRegistry
from .store import InMemoryWorkflowStore, WorkflowSessionStore
from .validation import validate_checkpoint

_OUTCOME_STATUS = {
    ControllerOutcome.COMPLETED: WorkflowStatus.COMPLETED,
    ControllerOutcome.BLOCKED: WorkflowStatus.BLOCKED,
    ControllerOutcome.FAILED: WorkflowStatus.FAILED,
    ControllerOutcome.ESCALATED: WorkflowStatus.ESCALATED,
    ControllerOutcome.CANCELLED: WorkflowStatus.CANCELLED,
}


class WorkflowEngine:
    def __init__(
        self,
        registry: WorkflowRegistry,
        controller: ControllerEngine,
        policy: WorkflowPolicy | None = None,
        store: WorkflowSessionStore | None = None,
    ) -> None:
        self.registry = registry
        self.controller = controller
        self.policy = policy or WorkflowPolicy()
        self.store = store or InMemoryWorkflowStore()

    def start(
        self,
        task: Task,
        workflow: str,
        version: str,
        objective: str,
        *,
        dependency_states: Mapping[str, TaskStatus],
        started_at: datetime,
        deadline: datetime | None = None,
        approval_evidence: tuple[str, ...] = (),
        max_fix_attempts: int | None = None,
    ) -> WorkflowSession:
        definition = self.registry.resolve(workflow, version)
        fix_budget = definition.max_fix_attempts if max_fix_attempts is None else max_fix_attempts
        self.policy.authorize(
            task,
            definition,
            dependency_states,
            now=started_at,
            deadline=deadline,
            approval_evidence=approval_evidence,
            max_fix_attempts=fix_budget,
        )
        if not objective.strip():
            raise WorkflowPolicyError("Workflow objective must not be empty")
        session_id = (
            f"workflow:{task.task_id}:{definition.name}:{definition.version}:"
            f"{int(started_at.timestamp() * 1_000_000)}"
        )
        event = WorkflowEvent(
            1,
            session_id,
            task.task_id,
            "WORKFLOW_STARTED",
            "CREATED",
            started_at,
            "Workflow policy and dependency gates passed",
            approval_evidence,
        )
        session = WorkflowSession(
            session_id,
            task.task_id,
            definition.name,
            definition.version,
            objective.strip(),
            WorkflowStatus.CREATED,
            started_at,
            started_at,
            deadline,
            definition.max_steps,
            fix_budget,
            approval_evidence,
            (event,),
        )
        self.store.save(session)
        return session

    def run(
        self,
        task: Task,
        workflow: str,
        version: str,
        objective: str,
        *,
        dependency_states: dict[str, TaskStatus],
        clock: Callable[[], datetime] | None = None,
        cancelled: Callable[[], bool] | None = None,
        deadline: datetime | None = None,
        approval_evidence: tuple[str, ...] = (),
        max_fix_attempts: int | None = None,
    ) -> WorkflowResult:
        now = clock or (lambda: datetime.now(UTC))
        session = self.start(
            task,
            workflow,
            version,
            objective,
            dependency_states=dependency_states,
            started_at=now(),
            deadline=deadline,
            approval_evidence=approval_evidence,
            max_fix_attempts=max_fix_attempts,
        )
        dispatched_steps = 0

        def guard_dispatch() -> None:
            nonlocal dispatched_steps
            if cancelled is not None and cancelled():
                raise WorkflowPolicyError("Workflow cancelled before Agent dispatch")
            if deadline is not None and now() >= deadline:
                raise WorkflowPolicyError("Workflow deadline expired before Agent dispatch")
            if dispatched_steps >= session.max_steps:
                raise WorkflowPolicyError(
                    f"Workflow step budget exhausted at {session.max_steps} dispatches"
                )
            dispatched_steps += 1

        try:
            controller_session, updated_task = self.controller.run_lifecycle(
                task,
                objective,
                dependency_states=dependency_states,
                clock=now,
                max_fix_attempts=session.max_fix_attempts,
                approval_evidence=approval_evidence,
                dispatch_guard=guard_dispatch,
            )
        except WorkflowPolicyError as policy_error:
            status = (
                WorkflowStatus.CANCELLED
                if "cancelled" in str(policy_error).casefold()
                else WorkflowStatus.ESCALATED
            )
            self._record_abort(session, status, str(policy_error), now())
            raise
        if controller_session.outcome is None:
            terminal_error = WorkflowPolicyError("Controller returned a non-terminal session")
            self._record_abort(session, WorkflowStatus.ESCALATED, str(terminal_error), now())
            raise terminal_error
        recorded_dispatches = sum(
            event.event_type is ControllerEventType.AGENT_DISPATCHED
            for event in controller_session.events
        )
        if recorded_dispatches != dispatched_steps:
            trace_error = WorkflowPolicyError(
                "Controller dispatch trace does not match Workflow budget accounting"
            )
            self._record_abort(session, WorkflowStatus.ESCALATED, str(trace_error), now())
            raise trace_error
        status = _OUTCOME_STATUS[controller_session.outcome]
        events = list(session.events)
        for item in controller_session.events:
            events.append(
                WorkflowEvent(
                    len(events) + 1,
                    session.session_id,
                    task.task_id,
                    item.event_type.value,
                    item.stage.value,
                    item.timestamp,
                    item.reason,
                    item.evidence,
                )
            )
        terminal = replace(
            session,
            status=status,
            updated_at=controller_session.updated_at,
            events=tuple(events),
            controller_session_id=controller_session.session_id,
        )
        self.store.save(terminal)
        return WorkflowResult(terminal, updated_task, controller_session)

    def _record_abort(
        self,
        session: WorkflowSession,
        status: WorkflowStatus,
        reason: str,
        timestamp: datetime,
    ) -> None:
        event = WorkflowEvent(
            len(session.events) + 1,
            session.session_id,
            session.task_id,
            "WORKFLOW_ABORTED",
            status.value,
            timestamp,
            reason,
        )
        self.store.save(
            replace(
                session,
                status=status,
                updated_at=timestamp,
                events=(*session.events, event),
            )
        )

    def validate_resume(self, session_id: str) -> WorkflowSession:
        session = self.store.get(session_id)
        definition = self.registry.resolve(session.workflow, session.workflow_version)
        validate_checkpoint(session, definition)
        return session
