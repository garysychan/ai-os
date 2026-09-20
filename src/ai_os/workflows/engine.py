"""Deterministic Workflow Engine over the existing Controller authority boundary."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime

from ai_os.agents import ExecutionStatus
from ai_os.controller import (
    ControllerEngine,
    ControllerEventType,
    ControllerOutcome,
    ControllerSession,
)
from ai_os.tasks import ReviewResult, Task, TaskStatus
from ai_os.workflow import TransitionContext

from .errors import WorkflowPolicyError
from .fingerprint import definition_fingerprint
from .models import (
    WorkflowDefinition,
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
            None,
            definition_fingerprint(definition),
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
        definition = self.registry.resolve(workflow, version)
        dispatched_steps = 0
        output_sections: tuple[tuple[str, str], ...] = ()

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
            if definition.driver == "controller_lifecycle":
                controller_session, updated_task = self.controller.run_lifecycle(
                    task,
                    objective,
                    dependency_states=dependency_states,
                    clock=now,
                    max_fix_attempts=session.max_fix_attempts,
                    approval_evidence=approval_evidence,
                    dispatch_guard=guard_dispatch,
                )
            elif definition.driver == "linear_stage_plan":
                controller_session, updated_task, output_sections = self._run_linear_stage_plan(
                    task,
                    definition,
                    objective,
                    dependency_states=dependency_states,
                    now=now,
                    approval_evidence=approval_evidence,
                    guard_dispatch=guard_dispatch,
                )
            else:  # validated registries make this unreachable; keep execution fail-closed.
                raise WorkflowPolicyError(f"unsupported Workflow driver: {definition.driver}")
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
        return WorkflowResult(
            terminal,
            updated_task,
            controller_session,
            definition.required_output_sections,
            output_sections,
        )

    def _run_linear_stage_plan(
        self,
        task: Task,
        definition: WorkflowDefinition,
        objective: str,
        *,
        dependency_states: dict[str, TaskStatus],
        now: Callable[[], datetime],
        approval_evidence: tuple[str, ...],
        guard_dispatch: Callable[[], None],
    ) -> tuple[ControllerSession, Task, tuple[tuple[str, str], ...]]:
        controller_session = self.controller.start(
            task,
            objective,
            dependency_states=dependency_states,
            started_at=now(),
            max_fix_attempts=0,
            approval_evidence=approval_evidence,
        )
        current = task
        evidence: list[str] = []
        output: dict[str, str] = {}
        for stage in definition.stages:
            if stage.capability.value == "review":
                invalid = self._output_contract_failure(definition, output)
                if invalid is not None:
                    return (
                        self.controller.terminate(
                            controller_session,
                            ControllerOutcome.ESCALATED,
                            timestamp=now(),
                            reason=invalid,
                        ),
                        current,
                        tuple(output.items()),
                    )
                controller_session, current = self.controller.transition(
                    controller_session,
                    current,
                    TaskStatus.REVIEW,
                    TransitionContext(
                        actor="Controller",
                        reason="Declared research stages completed",
                        evidence=tuple(evidence) or ("declared stage plan completed",),
                        tests_passed=True,
                        dependency_states=dependency_states,
                    ),
                    occurred_at=now(),
                )
            guard_dispatch()
            controller_session, result = self.controller.dispatch(
                controller_session,
                current,
                stage.capability,
                actor=stage.agent_role.value,
                dependency_states=dependency_states,
                timestamp=now(),
                requested_role=stage.agent_role,
                required_permission=stage.required_permission,
                evidence=(f"workflow-stage:{stage.name}",),
            )
            evidence.extend(result.handoff.evidence or (result.summary,))
            for name, content in result.output_sections:
                normalized_name = name.strip()
                normalized_content = content.strip()
                if normalized_name and normalized_content:
                    output[normalized_name] = normalized_content
            if result.status is not ExecutionStatus.SUCCESS:
                outcome = {
                    ExecutionStatus.BLOCKED: ControllerOutcome.BLOCKED,
                    ExecutionStatus.FAILED: ControllerOutcome.FAILED,
                    ExecutionStatus.ESCALATED: ControllerOutcome.ESCALATED,
                }[result.status]
                return (
                    self.controller.terminate(
                        controller_session,
                        outcome,
                        timestamp=now(),
                        reason=f"declared stage {stage.name} did not succeed",
                        findings=result.findings or result.errors,
                    ),
                    current,
                    tuple(output.items()),
                )
            if stage.capability.value == "review":
                if result.review_result is not ReviewResult.APPROVE:
                    return (
                        self.controller.terminate(
                            controller_session,
                            ControllerOutcome.ESCALATED,
                            timestamp=now(),
                            reason="Reviewer did not approve declared stage plan",
                            findings=result.findings,
                        ),
                        current,
                        tuple(output.items()),
                    )
                controller_session, current = self.controller.transition(
                    controller_session,
                    current,
                    TaskStatus.DONE,
                    TransitionContext(
                        actor="Controller",
                        reason="Reviewer approved declared stage plan",
                        evidence=tuple(evidence),
                        tests_passed=True,
                        review_result=ReviewResult.APPROVE,
                        dependency_states=dependency_states,
                    ),
                    occurred_at=now(),
                )
        return (
            self.controller.terminate(
                controller_session,
                ControllerOutcome.COMPLETED,
                timestamp=now(),
                reason="All declared Workflow stages completed",
            ),
            current,
            tuple(output.items()),
        )

    @staticmethod
    def _output_contract_failure(
        definition: WorkflowDefinition, output: dict[str, str]
    ) -> str | None:
        missing = tuple(
            section for section in definition.required_output_sections if not output.get(section)
        )
        if missing:
            return "Workflow output contract is missing: " + ", ".join(missing)
        return None

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
