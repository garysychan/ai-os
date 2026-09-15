"""Synchronous provider-neutral Controller orchestration engine."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from ai_os.agents import (
    AgentRole,
    AgentRuntime,
    Capability,
    ExecutionRequest,
    ExecutionResult,
    Permission,
)
from ai_os.tasks import ReviewResult, Task, TaskStatus
from ai_os.workflow import StateMachine, TransitionContext

from .models import (
    ControllerEventType,
    ControllerOutcome,
    ControllerSession,
    ControllerStage,
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
    ) -> None:
        self.runtime = runtime
        self.state_machine = state_machine or StateMachine()
        self.policy = policy or ControllerPolicy()

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
        self.policy.validate_start(
            task,
            objective,
            dependency_states,
            max_fix_attempts=max_fix_attempts,
        )
        return create_session(
            task,
            objective,
            started_at=started_at,
            max_fix_attempts=max_fix_attempts,
            approval_evidence=approval_evidence,
        )

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
        self.policy.require_dispatchable(session)
        stage = self.policy.stage_for(capability)
        if stage is ControllerStage.FIXING:
            self.policy.require_fix_available(session)
        dispatched = append_event(
            session,
            event_type=ControllerEventType.AGENT_DISPATCHED,
            stage=stage,
            actor=AgentRole.CONTROLLER,
            timestamp=timestamp,
            reason=f"Dispatch {capability.value}",
            evidence=evidence,
        )
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
        result = self.runtime.execute(request, dependency_states=dependency_states)
        return record_result(dispatched, result, stage=stage, timestamp=timestamp), result

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
        return record_transition(session, event), updated_task

    def terminate(
        self,
        session: ControllerSession,
        outcome: ControllerOutcome,
        *,
        timestamp: datetime,
        reason: str,
        findings: tuple[str, ...] = (),
    ) -> ControllerSession:
        return terminate_session(
            session,
            outcome,
            timestamp=timestamp,
            reason=reason,
            findings=findings,
        )
