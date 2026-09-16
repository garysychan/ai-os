"""End-to-end validation of the executable AI OS MVP."""

from __future__ import annotations

import unittest
from collections import deque
from datetime import UTC, datetime

from ai_os.agents import (
    Agent,
    AgentDescriptor,
    AgentRegistry,
    AgentRole,
    AgentRouter,
    AgentRuntime,
    Capability,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    Handoff,
    Permission,
    PermissionPolicy,
)
from ai_os.controller import ControllerEngine, ControllerOutcome, ControllerStage
from ai_os.execution import (
    AdapterRegistry,
    ExecutionContext,
    ExecutionEngine,
    ExecutionOutcome,
    ExecutionPlan,
    ExecutionStep,
    NoOpAdapter,
)
from ai_os.tasks import (
    AcceptanceCriterion,
    Priority,
    ReviewResult,
    Task,
    TaskStatus,
    validate_task,
)

NOW = datetime(2026, 9, 16, tzinfo=UTC)
DEPENDENCIES = {
    "TASK-0004": TaskStatus.DONE,
    "TASK-0005": TaskStatus.DONE,
    "TASK-0006": TaskStatus.DONE,
    "TASK-0010": TaskStatus.DONE,
    "TASK-0011": TaskStatus.DONE,
}


def mvp_task() -> Task:
    return validate_task(
        Task(
            task_id="TASK-0008",
            title="AI OS MVP Validation",
            priority=Priority.P1,
            status=TaskStatus.IN_PROGRESS,
            agents=("Developer", "Tester", "Reviewer", "Fixer"),
            dependencies=tuple(DEPENDENCIES),
            acceptance_criteria=(
                AcceptanceCriterion(
                    "MVP lifecycle is executable",
                    completed=True,
                    evidence=("tests/mvp/test_ai_os_mvp.py",),
                ),
            ),
        )
    )


def execution_plan() -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="mvp-plan",
        task_id="TASK-0008",
        max_steps=1,
        steps=(
            ExecutionStep(
                step_id="codex-implementation",
                adapter="codex-noop",
                operation="implement",
                agent_role=AgentRole.DEVELOPER,
                capability=Capability.IMPLEMENT,
                required_permission=Permission.MODIFY_CODE,
            ),
        ),
    )


class ExecutionBackedDeveloper(Agent):
    """Developer whose implementation delegates to the governed Execution Engine."""

    def __init__(self, execution_engine: ExecutionEngine) -> None:
        self.execution_engine = execution_engine
        policy = PermissionPolicy()
        self._descriptor = AgentDescriptor(
            role=AgentRole.DEVELOPER,
            capabilities=frozenset({Capability.IMPLEMENT}),
            permissions=policy.permissions_for(AgentRole.DEVELOPER),
            supported_statuses=frozenset({TaskStatus.IN_PROGRESS}),
            description="MVP execution-backed developer",
        )

    @property
    def descriptor(self) -> AgentDescriptor:
        return self._descriptor

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        session, result = self.execution_engine.run(
            request.task,
            execution_plan(),
            ExecutionContext(
                controller_session_id="mvp-controller",
                objective=request.objective,
                approval_evidence=("TASK-0008 authorized",),
            ),
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
        )
        succeeded = result.outcome is ExecutionOutcome.COMPLETED
        summary = f"Execution Engine: {result.outcome.value}"
        return ExecutionResult(
            task_id=request.task.task_id,
            role=AgentRole.DEVELOPER,
            capability=Capability.IMPLEMENT,
            status=ExecutionStatus.SUCCESS if succeeded else ExecutionStatus.FAILED,
            summary=summary,
            handoff=Handoff(
                task_id=request.task.task_id,
                state=request.task.status,
                objective=request.objective,
                completed=(summary,) if succeeded else (),
                artifacts=(session.execution_id,),
                tests=(),
                risks=(),
                remaining=() if succeeded else ("resolve execution failure",),
                next_action="Tester" if succeeded else "Controller",
                evidence=tuple(event.reason for event in session.events),
            ),
            findings=result.findings,
        )


class ScriptedGateAgent(Agent):
    def __init__(
        self,
        role: AgentRole,
        capability: Capability,
        statuses: tuple[ExecutionStatus, ...],
        reviews: tuple[ReviewResult | None, ...] = (),
    ) -> None:
        policy = PermissionPolicy()
        self._descriptor = AgentDescriptor(
            role=role,
            capabilities=frozenset({capability}),
            permissions=policy.permissions_for(role),
            supported_statuses=frozenset({TaskStatus.IN_PROGRESS, TaskStatus.REVIEW}),
            description="MVP scripted gate agent",
        )
        self.statuses = deque(statuses)
        self.reviews = deque(reviews)

    @property
    def descriptor(self) -> AgentDescriptor:
        return self._descriptor

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        status = self.statuses.popleft()
        review = self.reviews.popleft() if self.reviews else None
        summary = f"{self.descriptor.role.value}: {status.value}"
        return ExecutionResult(
            task_id=request.task.task_id,
            role=self.descriptor.role,
            capability=request.capability,
            status=status,
            summary=summary,
            handoff=Handoff(
                task_id=request.task.task_id,
                state=request.task.status,
                objective=request.objective,
                completed=(summary,),
                artifacts=(),
                tests=(summary,) if request.capability is Capability.TEST else (),
                risks=(),
                remaining=(),
                next_action="Controller",
                evidence=(summary,),
            ),
            review_result=review,
            findings=(summary,) if status is not ExecutionStatus.SUCCESS else (),
        )


def controller(
    *,
    test_statuses: tuple[ExecutionStatus, ...] = (ExecutionStatus.SUCCESS,),
    reviews: tuple[ReviewResult, ...] = (ReviewResult.APPROVE,),
    fix_statuses: tuple[ExecutionStatus, ...] = (ExecutionStatus.SUCCESS,),
) -> ControllerEngine:
    execution = ExecutionEngine(
        AdapterRegistry((NoOpAdapter("codex-noop", frozenset({"implement"})),))
    )
    agents = (
        ExecutionBackedDeveloper(execution),
        ScriptedGateAgent(AgentRole.TESTER, Capability.TEST, test_statuses),
        ScriptedGateAgent(
            AgentRole.REVIEWER,
            Capability.REVIEW,
            tuple(ExecutionStatus.SUCCESS for _ in reviews),
            reviews,
        ),
        ScriptedGateAgent(AgentRole.FIXER, Capability.FIX, fix_statuses),
    )
    return ControllerEngine(AgentRuntime(AgentRouter(AgentRegistry(agents))))


class AiOsMvpValidationTests(unittest.TestCase):
    def test_requirement_to_task_through_execution_and_review_reaches_done(self) -> None:
        session, completed = controller().run_lifecycle(
            mvp_task(),
            "Turn an approved requirement into reviewed executable evidence",
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
            approval_evidence=("TASK-0008 dependencies satisfied",),
        )

        self.assertEqual(completed.status, TaskStatus.DONE)
        self.assertEqual(session.outcome, ControllerOutcome.COMPLETED)
        self.assertEqual(session.stage, ControllerStage.TERMINAL)
        self.assertEqual(
            tuple(result.role for result in session.results),
            (AgentRole.DEVELOPER, AgentRole.TESTER, AgentRole.REVIEWER),
        )
        developer_handoff = session.results[0].handoff
        self.assertTrue(developer_handoff.artifacts)
        self.assertIn("Tester", developer_handoff.next_action)
        self.assertTrue(session.results[1].handoff.tests)
        self.assertEqual(session.results[2].review_result, ReviewResult.APPROVE)

    def test_test_failure_runs_finite_fixer_and_reenters_all_gates(self) -> None:
        session, completed = controller(
            test_statuses=(ExecutionStatus.FAILED, ExecutionStatus.SUCCESS),
        ).run_lifecycle(
            mvp_task(),
            "Validate the governed Fixer recovery path",
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
            max_fix_attempts=1,
        )

        self.assertEqual(completed.status, TaskStatus.DONE)
        self.assertEqual(session.fix_attempts, 1)
        self.assertEqual(
            tuple(result.role for result in session.results),
            (
                AgentRole.DEVELOPER,
                AgentRole.TESTER,
                AgentRole.FIXER,
                AgentRole.TESTER,
                AgentRole.REVIEWER,
            ),
        )

    def test_reviewer_block_and_fix_limit_escalation_are_terminal(self) -> None:
        blocked, blocked_task = controller(reviews=(ReviewResult.BLOCKED,)).run_lifecycle(
            mvp_task(),
            "Validate independent Reviewer blocking",
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
        )
        self.assertEqual(blocked.outcome, ControllerOutcome.BLOCKED)
        self.assertEqual(blocked_task.status, TaskStatus.REVIEW)

        escalated, active_task = controller(
            test_statuses=(ExecutionStatus.FAILED, ExecutionStatus.FAILED),
        ).run_lifecycle(
            mvp_task(),
            "Validate finite failure escalation",
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
            max_fix_attempts=1,
        )
        self.assertEqual(escalated.outcome, ControllerOutcome.ESCALATED)
        self.assertEqual(active_task.status, TaskStatus.IN_PROGRESS)
        self.assertTrue(escalated.blocking_findings)


if __name__ == "__main__":
    unittest.main()
