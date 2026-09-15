"""Execution Engine lifecycle and authority tests."""

import unittest
from collections import deque
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta

from ai_os.agents import AgentRole, Capability, Permission
from ai_os.execution import (
    AdapterRegistry,
    AdapterRegistryError,
    ExecutionContext,
    ExecutionEngine,
    ExecutionOutcome,
    ExecutionPlan,
    ExecutionPolicyError,
    ExecutionStep,
    NoOpAdapter,
    StepResult,
    StepStatus,
)
from ai_os.tasks import AcceptanceCriterion, Priority, Task, TaskStatus

NOW = datetime(2026, 9, 15, tzinfo=UTC)
DEPENDENCIES = {
    "TASK-0004": TaskStatus.DONE,
    "TASK-0005": TaskStatus.DONE,
    "TASK-0006": TaskStatus.DONE,
    "TASK-0010": TaskStatus.DONE,
}


def task() -> Task:
    return Task(
        task_id="TASK-0011",
        title="Execution Engine",
        priority=Priority.P1,
        status=TaskStatus.IN_PROGRESS,
        agents=("Controller", "Developer", "Tester", "Reviewer", "Fixer"),
        dependencies=tuple(DEPENDENCIES),
        acceptance_criteria=(AcceptanceCriterion("execution works"),),
    )


def step(*, retries: int = 0, idempotent: bool = False) -> ExecutionStep:
    return ExecutionStep(
        step_id="step-1",
        adapter="memory",
        operation="record",
        agent_role=AgentRole.DEVELOPER,
        capability=Capability.IMPLEMENT,
        required_permission=Permission.MODIFY_CODE,
        inputs=(("value", "safe"),),
        idempotent=idempotent,
        max_retries=retries,
    )


def plan(execution_step: ExecutionStep | None = None) -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="plan-1",
        task_id="TASK-0011",
        steps=(execution_step or step(),),
        max_steps=1,
    )


def context() -> ExecutionContext:
    return ExecutionContext(
        controller_session_id="controller-1",
        objective="execute approved plan",
        approval_evidence=("CR-2026-008 APPROVED",),
    )


class ScriptedAdapter:
    def __init__(
        self,
        statuses: tuple[StepStatus, ...],
        *,
        external: bool = False,
    ) -> None:
        self.statuses = deque(statuses)
        self._external = external

    @property
    def name(self) -> str:
        return "memory"

    @property
    def operations(self) -> frozenset[str]:
        return frozenset({"record"})

    @property
    def has_external_side_effects(self) -> bool:
        return self._external

    def execute(
        self,
        execution_step: ExecutionStep,
        execution_context: ExecutionContext,
        attempt: int,
    ) -> StepResult:
        status = self.statuses.popleft()
        return StepResult(
            step_id=execution_step.step_id,
            attempt=attempt,
            status=status,
            summary=f"attempt {attempt}: {status.value}",
            evidence=(execution_context.objective,),
            errors=("scripted failure",) if status is not StepStatus.SUCCESS else (),
        )


class ExecutionEngineTests(unittest.TestCase):
    def test_success_is_deterministic_immutable_and_does_not_mutate_task(self) -> None:
        original = task()
        engine = ExecutionEngine(AdapterRegistry((NoOpAdapter("memory", frozenset({"record"})),)))
        session, result = engine.run(
            original,
            plan(),
            context(),
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
        )
        self.assertEqual(result.outcome, ExecutionOutcome.COMPLETED)
        self.assertEqual(original.status, TaskStatus.IN_PROGRESS)
        self.assertEqual(tuple(event.sequence for event in session.events), (1, 2, 3, 4))
        self.assertEqual(session.execution_id, result.execution_id)
        with self.assertRaises(FrozenInstanceError):
            session.outcome = None  # type: ignore[misc]

    def test_idempotent_failure_retries_and_preserves_every_attempt(self) -> None:
        adapter = ScriptedAdapter((StepStatus.FAILED, StepStatus.SUCCESS))
        session, result = ExecutionEngine(AdapterRegistry((adapter,))).run(
            task(),
            plan(step(retries=1, idempotent=True)),
            context(),
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
        )
        self.assertEqual(result.outcome, ExecutionOutcome.COMPLETED)
        self.assertEqual(tuple(item.attempt for item in session.results), (1, 2))
        self.assertEqual(session.results[0].errors, ("scripted failure",))

    def test_non_idempotent_retry_is_denied(self) -> None:
        with self.assertRaisesRegex(ExecutionPolicyError, "non-idempotent"):
            ExecutionEngine(AdapterRegistry((NoOpAdapter("memory", frozenset({"record"})),))).run(
                task(),
                plan(step(retries=1)),
                context(),
                dependency_states=DEPENDENCIES,
                clock=lambda: NOW,
            )

    def test_external_adapter_and_unknown_adapter_are_default_denied(self) -> None:
        with self.assertRaisesRegex(ExecutionPolicyError, "side-effect"):
            ExecutionEngine(
                AdapterRegistry((ScriptedAdapter((StepStatus.SUCCESS,), external=True),))
            ).run(task(), plan(), context(), dependency_states=DEPENDENCIES, clock=lambda: NOW)
        with self.assertRaisesRegex(AdapterRegistryError, "unknown adapter"):
            ExecutionEngine(AdapterRegistry()).run(
                task(), plan(), context(), dependency_states=DEPENDENCIES, clock=lambda: NOW
            )

    def test_blocked_failed_and_escalated_outcomes_are_preserved(self) -> None:
        for status, expected in (
            (StepStatus.BLOCKED, ExecutionOutcome.BLOCKED),
            (StepStatus.FAILED, ExecutionOutcome.FAILED),
            (StepStatus.ESCALATED, ExecutionOutcome.ESCALATED),
        ):
            with self.subTest(status=status):
                _, result = ExecutionEngine(AdapterRegistry((ScriptedAdapter((status,)),))).run(
                    task(), plan(), context(), dependency_states=DEPENDENCIES, clock=lambda: NOW
                )
                self.assertEqual(result.outcome, expected)

    def test_cancellation_stops_before_adapter_execution(self) -> None:
        adapter = ScriptedAdapter((StepStatus.SUCCESS,))
        session, result = ExecutionEngine(AdapterRegistry((adapter,))).run(
            task(),
            plan(),
            context(),
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
            cancelled=lambda: True,
        )
        self.assertEqual(result.outcome, ExecutionOutcome.CANCELLED)
        self.assertEqual(session.results, ())
        self.assertEqual(len(adapter.statuses), 1)

    def test_expired_deadline_and_step_budget_are_rejected(self) -> None:
        expired = replace(context(), deadline=NOW - timedelta(seconds=1))
        engine = ExecutionEngine(AdapterRegistry((NoOpAdapter("memory", frozenset({"record"})),)))
        with self.assertRaisesRegex(ExecutionPolicyError, "deadline"):
            engine.run(task(), plan(), expired, dependency_states=DEPENDENCIES, clock=lambda: NOW)
        over_budget = replace(plan(), steps=(step(), replace(step(), step_id="step-2")))
        with self.assertRaisesRegex(ExecutionPolicyError, "step budget"):
            engine.run(
                task(), over_budget, context(), dependency_states=DEPENDENCIES, clock=lambda: NOW
            )

    def test_assignment_permission_and_registry_uniqueness_are_enforced(self) -> None:
        unassigned = replace(step(), agent_role=AgentRole.RESEARCHER)
        engine = ExecutionEngine(AdapterRegistry((NoOpAdapter("memory", frozenset({"record"})),)))
        with self.assertRaisesRegex(ExecutionPolicyError, "not assigned"):
            engine.run(
                task(),
                plan(unassigned),
                context(),
                dependency_states=DEPENDENCIES,
                clock=lambda: NOW,
            )
        unauthorized = replace(step(), required_permission=Permission.APPROVE_REVIEW)
        with self.assertRaisesRegex(ExecutionPolicyError, "requires modify_code"):
            engine.run(
                task(),
                plan(unauthorized),
                context(),
                dependency_states=DEPENDENCIES,
                clock=lambda: NOW,
            )
        mismatched_capability = replace(
            step(), capability=Capability.REVIEW, required_permission=Permission.APPROVE_REVIEW
        )
        with self.assertRaisesRegex(ExecutionPolicyError, "not authorized"):
            engine.run(
                task(),
                plan(mismatched_capability),
                context(),
                dependency_states=DEPENDENCIES,
                clock=lambda: NOW,
            )
        with self.assertRaisesRegex(AdapterRegistryError, "duplicate adapter"):
            AdapterRegistry(
                (
                    NoOpAdapter("memory", frozenset({"record"})),
                    NoOpAdapter("memory", frozenset({"record"})),
                )
            )


if __name__ == "__main__":
    unittest.main()
