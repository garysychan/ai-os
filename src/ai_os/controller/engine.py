"""Synchronous provider-neutral Controller orchestration engine."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime

from ai_os.agents import (
    AgentRole,
    AgentRuntime,
    AgentRuntimeError,
    Capability,
    ExecutionRequest,
    ExecutionResult,
    Permission,
)
from ai_os.tasks import ReviewResult, Task, TaskStatus
from ai_os.workflow import StateMachine, TransitionContext

from .errors import ControllerError, ControllerPolicyError
from .models import (
    ControllerEventType,
    ControllerOutcome,
    ControllerSession,
    ControllerStage,
    TraceEvent,
)
from .policy import ControllerPolicy
from .session import (
    append_event,
    create_session,
    record_result,
    record_transition,
    terminate_session,
)


class ControllerEngine:
    """Coordinate existing runtime services without performing external side effects."""

    def __init__(
        self,
        runtime: AgentRuntime,
        state_machine: StateMachine | None = None,
        policy: ControllerPolicy | None = None,
        event_sink: Callable[[TraceEvent, ControllerOutcome | None], None] | None = None,
        denial_sink: Callable[[str, datetime, str], None] | None = None,
    ) -> None:
        self.runtime = runtime
        self.state_machine = state_machine or StateMachine()
        self.policy = policy or ControllerPolicy()
        self.event_sink = event_sink
        self.denial_sink = denial_sink

    def start(
        self,
        task: Task,
        objective: str,
        *,
        dependency_states: Mapping[str, TaskStatus],
        started_at: datetime,
        max_fix_attempts: int = 2,
        approval_evidence: tuple[str, ...] = (),
    ) -> ControllerSession:
        try:
            self.policy.validate_start(
                task,
                objective,
                dependency_states,
                max_fix_attempts=max_fix_attempts,
            )
        except ControllerError as error:
            self._deny(task.task_id, started_at, type(error).__name__)
            raise
        session = create_session(
            task,
            objective,
            started_at=started_at,
            max_fix_attempts=max_fix_attempts,
            approval_evidence=approval_evidence,
        )
        self._emit(session.events[-1], None)
        return session

    def dispatch(
        self,
        session: ControllerSession,
        task: Task,
        capability: Capability,
        *,
        actor: str,
        dependency_states: dict[str, TaskStatus],
        timestamp: datetime,
        requested_role: AgentRole | None = None,
        required_permission: Permission | None = None,
        review_result: ReviewResult | None = None,
        evidence: tuple[str, ...] = (),
    ) -> tuple[ControllerSession, ExecutionResult]:
        try:
            self.policy.require_dispatchable(session)
            stage = self.policy.stage_for(capability)
            if stage is ControllerStage.FIXING:
                self.policy.require_fix_available(session)
        except ControllerError as error:
            self._deny(task.task_id, timestamp, type(error).__name__)
            raise
        dispatched = append_event(
            session,
            event_type=ControllerEventType.AGENT_DISPATCHED,
            stage=stage,
            actor=AgentRole.CONTROLLER,
            timestamp=timestamp,
            reason=f"Dispatch {capability.value}",
            evidence=evidence,
        )
        self._emit(dispatched.events[-1], None)
        request = ExecutionRequest(
            task=task,
            capability=capability,
            objective=session.objective,
            actor=actor,
            requested_role=requested_role,
            required_permission=required_permission,
            review_result=review_result,
            evidence=evidence,
        )
        try:
            result = self.runtime.execute(request, dependency_states=dependency_states)
        except AgentRuntimeError as error:
            self._deny(task.task_id, timestamp, type(error).__name__)
            raise
        recorded = record_result(dispatched, result, stage=stage, timestamp=timestamp)
        self._emit(recorded.events[-1], None)
        return recorded, result

    def transition(
        self,
        session: ControllerSession,
        task: Task,
        target: TaskStatus,
        context: TransitionContext,
        *,
        occurred_at: datetime,
    ) -> tuple[ControllerSession, Task]:
        self.policy.require_dispatchable(session)
        updated_task, event = self.state_machine.transition(
            task,
            target,
            context,
            occurred_at=occurred_at,
        )
        recorded = record_transition(session, event)
        self._emit(recorded.events[-1], None)
        return recorded, updated_task

    def terminate(
        self,
        session: ControllerSession,
        outcome: ControllerOutcome,
        *,
        timestamp: datetime,
        reason: str,
        findings: tuple[str, ...] = (),
    ) -> ControllerSession:
        terminal = terminate_session(
            session,
            outcome,
            timestamp=timestamp,
            reason=reason,
            findings=findings,
        )
        self._emit(terminal.events[-1], outcome)
        return terminal

    def _emit(self, event: TraceEvent, outcome: ControllerOutcome | None) -> None:
        if self.event_sink is not None:
            with suppress(Exception):
                self.event_sink(event, outcome)

    def _deny(self, task_id: str, timestamp: datetime, reason: str) -> None:
        if self.denial_sink is not None:
            with suppress(Exception):
                self.denial_sink(task_id, timestamp, reason)

    def run_lifecycle(
        self,
        task: Task,
        objective: str,
        *,
        dependency_states: dict[str, TaskStatus],
        clock: Callable[[], datetime] | None = None,
        max_fix_attempts: int = 2,
        approval_evidence: tuple[str, ...] = (),
        dispatch_guard: Callable[[], None] | None = None,
    ) -> tuple[ControllerSession, Task]:
        """Run the synchronous implement/test/review lifecycle to a terminal outcome."""
        now = clock or (lambda: datetime.now(UTC))
        session = self.start(
            task,
            objective,
            dependency_states=dependency_states,
            started_at=now(),
            max_fix_attempts=max_fix_attempts,
            approval_evidence=approval_evidence,
        )
        current = task
        if dispatch_guard is not None:
            dispatch_guard()
        session, implementation = self.dispatch(
            session,
            current,
            Capability.IMPLEMENT,
            actor="Developer",
            dependency_states=dependency_states,
            timestamp=now(),
            requested_role=AgentRole.DEVELOPER,
        )
        if self.policy.result_is_blocking(implementation.status):
            return self._terminal_from_result(session, current, implementation, now())

        while True:
            if dispatch_guard is not None:
                dispatch_guard()
            session, test_result = self.dispatch(
                session,
                current,
                Capability.TEST,
                actor="Tester",
                dependency_states=dependency_states,
                timestamp=now(),
                requested_role=AgentRole.TESTER,
            )
            if self.policy.result_is_blocking(test_result.status):
                fixed = self._attempt_fix(
                    session,
                    current,
                    dependency_states=dependency_states,
                    timestamp=now(),
                    dispatch_guard=dispatch_guard,
                )
                if fixed is None:
                    return (
                        self.terminate(
                            session,
                            ControllerOutcome.ESCALATED,
                            timestamp=now(),
                            reason="test failure exhausted finite fix limit",
                            findings=test_result.findings or test_result.errors,
                        ),
                        current,
                    )
                session = fixed
                continue

            session, current = self.transition(
                session,
                current,
                TaskStatus.REVIEW,
                TransitionContext(
                    actor="Controller",
                    reason="Tester gate passed",
                    evidence=test_result.handoff.evidence or (test_result.summary,),
                    tests_passed=True,
                    dependency_states=dependency_states,
                ),
                occurred_at=now(),
            )
            if dispatch_guard is not None:
                dispatch_guard()
            session, review = self.dispatch(
                session,
                current,
                Capability.REVIEW,
                actor="Reviewer",
                dependency_states=dependency_states,
                timestamp=now(),
                requested_role=AgentRole.REVIEWER,
            )
            if review.review_result is ReviewResult.REQUEST_CHANGES:
                session, current = self.transition(
                    session,
                    current,
                    TaskStatus.IN_PROGRESS,
                    TransitionContext(
                        actor="Reviewer",
                        reason="Reviewer requested changes",
                        evidence=review.handoff.evidence,
                    ),
                    occurred_at=now(),
                )
                fixed = self._attempt_fix(
                    session,
                    current,
                    dependency_states=dependency_states,
                    timestamp=now(),
                    dispatch_guard=dispatch_guard,
                )
                if fixed is None:
                    return (
                        self.terminate(
                            session,
                            ControllerOutcome.ESCALATED,
                            timestamp=now(),
                            reason="review changes exhausted finite fix limit",
                            findings=review.findings,
                        ),
                        current,
                    )
                session = fixed
                continue
            if review.review_result is ReviewResult.BLOCKED:
                return (
                    self.terminate(
                        session,
                        ControllerOutcome.BLOCKED,
                        timestamp=now(),
                        reason="Reviewer blocked completion",
                        findings=review.findings,
                    ),
                    current,
                )
            if review.review_result is not ReviewResult.APPROVE:
                return (
                    self.terminate(
                        session,
                        ControllerOutcome.FAILED,
                        timestamp=now(),
                        reason="Reviewer produced no valid decision",
                    ),
                    current,
                )

            completion_task = replace(
                current,
                completion_evidence=(test_result.summary, review.summary),
            )
            session, completed = self.transition(
                session,
                completion_task,
                TaskStatus.DONE,
                TransitionContext(
                    actor="Controller",
                    reason="Reviewer approved completion",
                    evidence=(test_result.summary, review.summary),
                    tests_passed=True,
                    review_result=ReviewResult.APPROVE,
                    dependency_states=dependency_states,
                ),
                occurred_at=now(),
            )
            return (
                self.terminate(
                    session,
                    ControllerOutcome.COMPLETED,
                    timestamp=now(),
                    reason="all completion gates passed",
                ),
                completed,
            )

    def _attempt_fix(
        self,
        session: ControllerSession,
        task: Task,
        *,
        dependency_states: dict[str, TaskStatus],
        timestamp: datetime,
        dispatch_guard: Callable[[], None] | None = None,
    ) -> ControllerSession | None:
        try:
            if dispatch_guard is not None:
                dispatch_guard()
            session, result = self.dispatch(
                session,
                task,
                Capability.FIX,
                actor="Fixer",
                dependency_states=dependency_states,
                timestamp=timestamp,
                requested_role=AgentRole.FIXER,
            )
        except ControllerPolicyError:
            return None
        if self.policy.result_is_blocking(result.status):
            return None
        return session

    def _terminal_from_result(
        self,
        session: ControllerSession,
        task: Task,
        result: ExecutionResult,
        timestamp: datetime,
    ) -> tuple[ControllerSession, Task]:
        outcomes = {
            "BLOCKED": ControllerOutcome.BLOCKED,
            "FAILED": ControllerOutcome.FAILED,
            "ESCALATED": ControllerOutcome.ESCALATED,
        }
        return (
            self.terminate(
                session,
                outcomes[result.status.value],
                timestamp=timestamp,
                reason=result.summary,
                findings=result.findings or result.errors,
            ),
            task,
        )
