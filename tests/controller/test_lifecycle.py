"""End-to-end Controller lifecycle tests with provider-neutral scripted Agents."""

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
    PermissionPolicy,
)
from ai_os.controller import ControllerEngine, ControllerOutcome
from ai_os.tasks import AcceptanceCriterion, Priority, ReviewResult, Task, TaskStatus

NOW = datetime(2026, 9, 15, tzinfo=UTC)
DEPENDENCIES = {"TASK-0004": TaskStatus.DONE, "TASK-0006": TaskStatus.DONE}
CAPABILITIES = {
    AgentRole.DEVELOPER: Capability.IMPLEMENT,
    AgentRole.TESTER: Capability.TEST,
    AgentRole.REVIEWER: Capability.REVIEW,
    AgentRole.FIXER: Capability.FIX,
}


class ScriptedAgent(Agent):
    def __init__(
        self,
        role: AgentRole,
        statuses: tuple[ExecutionStatus, ...],
        reviews: tuple[ReviewResult | None, ...] = (),
    ) -> None:
        policy = PermissionPolicy()
        self._descriptor = AgentDescriptor(
            role=role,
            capabilities=frozenset({CAPABILITIES[role]}),
            permissions=policy.permissions_for(role),
            supported_statuses=frozenset({TaskStatus.IN_PROGRESS, TaskStatus.REVIEW}),
            description="scripted test agent",
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


def task() -> Task:
    return Task(
        task_id="TASK-0010",
        title="Controller lifecycle",
        priority=Priority.P1,
        status=TaskStatus.IN_PROGRESS,
        agents=("Developer", "Tester", "Reviewer", "Fixer"),
        dependencies=tuple(DEPENDENCIES),
        acceptance_criteria=(AcceptanceCriterion("lifecycle works"),),
    )


def engine(
    *,
    tests: tuple[ExecutionStatus, ...],
    reviews: tuple[ReviewResult, ...],
    fixes: tuple[ExecutionStatus, ...] = (),
    implementation: ExecutionStatus = ExecutionStatus.SUCCESS,
) -> ControllerEngine:
    agents = (
        ScriptedAgent(AgentRole.DEVELOPER, (implementation,)),
        ScriptedAgent(AgentRole.TESTER, tests),
        ScriptedAgent(
            AgentRole.REVIEWER,
            tuple(ExecutionStatus.SUCCESS for _ in reviews),
            reviews,
        ),
        ScriptedAgent(AgentRole.FIXER, fixes or (ExecutionStatus.SUCCESS,)),
    )
    return ControllerEngine(AgentRuntime(AgentRouter(AgentRegistry(agents))))


class LifecycleTests(unittest.TestCase):
    def test_successful_lifecycle_reaches_done(self) -> None:
        session, completed = engine(
            tests=(ExecutionStatus.SUCCESS,),
            reviews=(ReviewResult.APPROVE,),
        ).run_lifecycle(
            task(),
            "complete lifecycle",
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
        )
        self.assertEqual(completed.status, TaskStatus.DONE)
        self.assertEqual(session.outcome, ControllerOutcome.COMPLETED)
        self.assertEqual(session.task_status, TaskStatus.DONE)
        self.assertTrue(completed.acceptance_criteria[0].completed)

    def test_test_failure_runs_fixer_and_retests(self) -> None:
        session, completed = engine(
            tests=(ExecutionStatus.FAILED, ExecutionStatus.SUCCESS),
            reviews=(ReviewResult.APPROVE,),
        ).run_lifecycle(
            task(),
            "fix test",
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
        )
        self.assertEqual(completed.status, TaskStatus.DONE)
        self.assertEqual(session.fix_attempts, 1)

    def test_review_request_changes_runs_fixer_and_returns_to_review(self) -> None:
        session, completed = engine(
            tests=(ExecutionStatus.SUCCESS, ExecutionStatus.SUCCESS),
            reviews=(ReviewResult.REQUEST_CHANGES, ReviewResult.APPROVE),
        ).run_lifecycle(
            task(),
            "fix review",
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
        )
        self.assertEqual(completed.status, TaskStatus.DONE)
        self.assertEqual(session.fix_attempts, 1)
        self.assertEqual(len(session.transitions), 4)

    def test_reviewer_blocked_stops_session(self) -> None:
        session, current = engine(
            tests=(ExecutionStatus.SUCCESS,),
            reviews=(ReviewResult.BLOCKED,),
        ).run_lifecycle(
            task(),
            "blocked review",
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
        )
        self.assertEqual(current.status, TaskStatus.REVIEW)
        self.assertEqual(session.outcome, ControllerOutcome.BLOCKED)

    def test_finite_fix_limit_escalates(self) -> None:
        session, current = engine(
            tests=(ExecutionStatus.FAILED, ExecutionStatus.FAILED),
            reviews=(),
        ).run_lifecycle(
            task(),
            "finite fixes",
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
            max_fix_attempts=1,
        )
        self.assertEqual(current.status, TaskStatus.IN_PROGRESS)
        self.assertEqual(session.outcome, ControllerOutcome.ESCALATED)
        self.assertEqual(session.fix_attempts, 1)

    def test_implementation_failure_is_terminal(self) -> None:
        session, current = engine(
            tests=(),
            reviews=(),
            implementation=ExecutionStatus.FAILED,
        ).run_lifecycle(
            task(),
            "failed implementation",
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
        )
        self.assertEqual(current.status, TaskStatus.IN_PROGRESS)
        self.assertEqual(session.outcome, ControllerOutcome.FAILED)


if __name__ == "__main__":
    unittest.main()
