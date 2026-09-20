"""Tests for the side-effect-free Controller orchestration slice."""

import unittest
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

from ai_os.agents import (
    AgentRegistry,
    AgentRole,
    AgentRouter,
    AgentRuntime,
    Capability,
    ExecutionStatus,
    canonical_agents,
)
from ai_os.controller import (
    ControllerEngine,
    ControllerOutcome,
    ControllerPolicyError,
    ControllerStage,
    ControllerValidationError,
    create_session,
    make_trace_event,
)
from ai_os.tasks import AcceptanceCriterion, Priority, Task, TaskStatus
from ai_os.workflow import TransitionContext

NOW = datetime(2026, 9, 15, tzinfo=UTC)
DEPENDENCIES = {"TASK-0004": TaskStatus.DONE, "TASK-0006": TaskStatus.DONE}


def task_in(status: TaskStatus, *, agents: tuple[str, ...] = ("Developer",)) -> Task:
    return Task(
        task_id="TASK-0010",
        title="Controller",
        priority=Priority.P1,
        status=status,
        agents=agents,
        dependencies=("TASK-0004", "TASK-0006"),
        acceptance_criteria=(AcceptanceCriterion("works"),),
    )


class ControllerEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = AgentRegistry(canonical_agents())
        self.engine = ControllerEngine(AgentRuntime(AgentRouter(registry)))

    def test_start_is_deterministic_and_immutable(self) -> None:
        task = task_in(TaskStatus.IN_PROGRESS)
        first = self.engine.start(
            task,
            "coordinate",
            dependency_states=DEPENDENCIES,
            started_at=NOW,
        )
        second = self.engine.start(
            task,
            "coordinate",
            dependency_states=DEPENDENCIES,
            started_at=NOW,
        )
        self.assertEqual(first.session_id, second.session_id)
        self.assertEqual(first.stage, ControllerStage.CREATED)
        self.assertEqual(first.events[0].sequence, 1)
        with self.assertRaises(FrozenInstanceError):
            first.objective = "changed"  # type: ignore[misc]

    def test_start_rejects_state_dependency_and_objective(self) -> None:
        with self.assertRaises(ControllerPolicyError):
            self.engine.start(
                task_in(TaskStatus.TODO),
                "coordinate",
                dependency_states=DEPENDENCIES,
                started_at=NOW,
            )
        with self.assertRaises(ControllerPolicyError):
            self.engine.start(
                task_in(TaskStatus.IN_PROGRESS),
                "coordinate",
                dependency_states={},
                started_at=NOW,
            )
        with self.assertRaises(ControllerPolicyError):
            self.engine.start(
                task_in(TaskStatus.IN_PROGRESS),
                " ",
                dependency_states=DEPENDENCIES,
                started_at=NOW,
            )

    def test_start_policy_denial_is_emitted(self) -> None:
        denied: list[tuple[str, str]] = []
        registry = AgentRegistry(canonical_agents())
        engine = ControllerEngine(
            AgentRuntime(AgentRouter(registry)),
            denial_sink=lambda task_id, _timestamp, reason: denied.append((task_id, reason)),
        )
        with self.assertRaises(ControllerPolicyError):
            engine.start(
                task_in(TaskStatus.TODO),
                "coordinate",
                dependency_states=DEPENDENCIES,
                started_at=NOW,
            )
        self.assertEqual(denied, [("TASK-0010", "ControllerPolicyError")])

    def test_dispatch_policy_denial_is_emitted(self) -> None:
        denied: list[tuple[str, str]] = []
        registry = AgentRegistry(canonical_agents())
        engine = ControllerEngine(
            AgentRuntime(AgentRouter(registry)),
            denial_sink=lambda task_id, _timestamp, reason: denied.append((task_id, reason)),
        )
        task = task_in(TaskStatus.IN_PROGRESS)
        session = engine.start(task, "coordinate", dependency_states=DEPENDENCIES, started_at=NOW)
        terminal = engine.terminate(
            session, ControllerOutcome.CANCELLED, timestamp=NOW, reason="cancelled"
        )
        with self.assertRaises(ControllerPolicyError):
            engine.dispatch(
                terminal,
                task,
                Capability.IMPLEMENT,
                actor="Developer",
                dependency_states=DEPENDENCIES,
                timestamp=NOW,
            )
        self.assertEqual(denied, [("TASK-0010", "ControllerPolicyError")])

    def test_dispatch_uses_runtime_and_records_ordered_trace(self) -> None:
        task = task_in(TaskStatus.IN_PROGRESS)
        session = self.engine.start(
            task,
            "implement",
            dependency_states=DEPENDENCIES,
            started_at=NOW,
        )
        session, result = self.engine.dispatch(
            session,
            task,
            Capability.IMPLEMENT,
            actor="developer",
            dependency_states=DEPENDENCIES,
            timestamp=NOW,
            requested_role=AgentRole.DEVELOPER,
            evidence=("scope approved",),
        )
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        self.assertEqual(session.stage, ControllerStage.EXECUTING)
        self.assertEqual(tuple(event.sequence for event in session.events), (1, 2, 3))
        self.assertEqual(session.results, (result,))

    def test_transition_delegates_to_state_machine(self) -> None:
        task = task_in(TaskStatus.IN_PROGRESS)
        session = self.engine.start(
            task,
            "review",
            dependency_states=DEPENDENCIES,
            started_at=NOW,
        )
        session, updated = self.engine.transition(
            session,
            task,
            TaskStatus.REVIEW,
            TransitionContext(actor="Controller", reason="tests passed", evidence=("run",)),
            occurred_at=NOW,
        )
        self.assertEqual(updated.status, TaskStatus.REVIEW)
        self.assertEqual(session.task_status, TaskStatus.REVIEW)
        self.assertEqual(len(session.transitions), 1)

    def test_fix_limit_and_terminal_gate_are_enforced(self) -> None:
        task = task_in(TaskStatus.IN_PROGRESS, agents=("Fixer",))
        session = self.engine.start(
            task,
            "fix",
            dependency_states=DEPENDENCIES,
            started_at=NOW,
            max_fix_attempts=1,
        )
        session, _ = self.engine.dispatch(
            session,
            task,
            Capability.FIX,
            actor="fixer",
            dependency_states=DEPENDENCIES,
            timestamp=NOW,
            requested_role=AgentRole.FIXER,
        )
        with self.assertRaises(ControllerPolicyError):
            self.engine.dispatch(
                session,
                task,
                Capability.FIX,
                actor="fixer",
                dependency_states=DEPENDENCIES,
                timestamp=NOW,
                requested_role=AgentRole.FIXER,
            )
        terminal = self.engine.terminate(
            session,
            ControllerOutcome.ESCALATED,
            timestamp=NOW,
            reason="limit reached",
            findings=("failure",),
        )
        self.assertEqual(terminal.stage, ControllerStage.TERMINAL)
        self.assertEqual(terminal.blocking_findings, ("failure",))
        with self.assertRaises(ControllerPolicyError):
            self.engine.dispatch(
                terminal,
                task,
                Capability.FIX,
                actor="fixer",
                dependency_states=DEPENDENCIES,
                timestamp=NOW,
            )
        with self.assertRaises(ControllerValidationError):
            self.engine.terminate(
                terminal,
                ControllerOutcome.CANCELLED,
                timestamp=NOW,
                reason="again",
            )

    def test_validation_rejects_bad_session_and_trace_values(self) -> None:
        with self.assertRaises(ControllerValidationError):
            create_session(
                task_in(TaskStatus.IN_PROGRESS),
                "objective",
                started_at=NOW,
                max_fix_attempts=-1,
            )
        with self.assertRaises(ControllerValidationError):
            make_trace_event(
                sequence=0,
                session_id="session",
                task_id="TASK-0010",
                event_type=self.engine.start(
                    task_in(TaskStatus.IN_PROGRESS),
                    "x",
                    dependency_states=DEPENDENCIES,
                    started_at=NOW,
                )
                .events[0]
                .event_type,
                stage=ControllerStage.CREATED,
                actor=AgentRole.CONTROLLER,
                timestamp=NOW,
                reason="start",
            )


if __name__ == "__main__":
    unittest.main()
