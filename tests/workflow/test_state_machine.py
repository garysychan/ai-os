"""Tests for immutable workflow state transitions and DONE gates."""

from dataclasses import replace
from datetime import datetime, timezone
import unittest

from ai_os.tasks import (
    AcceptanceCriterion,
    Priority,
    ReviewResult,
    Task,
    TaskStatus,
)
from ai_os.workflow import (
    CompletionGateError,
    InvalidTransitionError,
    StateMachine,
    TransitionContext,
    TransitionValidationError,
)


def task_in(
    status: TaskStatus,
    *,
    criteria_complete: bool = False,
    dependencies: tuple[str, ...] = (),
) -> Task:
    return Task(
        task_id="TASK-0010",
        title="State Machine",
        priority=Priority.P1,
        status=status,
        agents=("Developer",),
        dependencies=dependencies,
        acceptance_criteria=(
            AcceptanceCriterion(
                "Tests pass",
                completed=criteria_complete,
                evidence=("CI-123",) if criteria_complete else (),
            ),
        ),
    )


def approved_context(**changes: object) -> TransitionContext:
    values: dict[str, object] = {
        "actor": "Reviewer",
        "reason": "All gates passed",
        "evidence": ("CI-123", "PR-10"),
        "tests_passed": True,
        "review_result": ReviewResult.APPROVE,
        "blocking_findings": (),
        "dependency_states": {},
    }
    values.update(changes)
    return TransitionContext(**values)  # type: ignore[arg-type]


class StateMachineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.machine = StateMachine()

    def test_transition_returns_new_task_and_aware_event(self) -> None:
        original = task_in(TaskStatus.TODO)
        updated, event = self.machine.transition(
            original,
            TaskStatus.IN_PROGRESS,
            TransitionContext(
                actor="Developer",
                reason="Implementation started",
                evidence=("CR-2026-005",),
            ),
        )

        self.assertIs(original.status, TaskStatus.TODO)
        self.assertIs(updated.status, TaskStatus.IN_PROGRESS)
        self.assertIs(event.source, TaskStatus.TODO)
        self.assertIs(event.target, TaskStatus.IN_PROGRESS)
        self.assertEqual(event.task_id, original.task_id)
        self.assertIsNotNone(event.timestamp.utcoffset())

    def test_invalid_transition_is_rejected(self) -> None:
        with self.assertRaises(InvalidTransitionError):
            self.machine.transition(
                task_in(TaskStatus.TODO),
                TaskStatus.DONE,
                approved_context(),
            )

    def test_review_to_done_passes_all_gates(self) -> None:
        original = task_in(
            TaskStatus.REVIEW,
            criteria_complete=True,
            dependencies=("TASK-0007",),
        )
        context = approved_context(
            dependency_states={"TASK-0007": TaskStatus.DONE}
        )

        updated, event = self.machine.transition(
            original,
            TaskStatus.DONE,
            context,
        )

        self.assertIs(updated.status, TaskStatus.DONE)
        self.assertEqual(updated.completion_evidence, ("CI-123", "PR-10"))
        self.assertEqual(event.evidence, ("CI-123", "PR-10"))

    def test_done_gate_reports_all_failures(self) -> None:
        task = task_in(
            TaskStatus.REVIEW,
            dependencies=("TASK-0007",),
        )
        context = TransitionContext(
            actor="Reviewer",
            reason="Premature completion",
            tests_passed=False,
            review_result=ReviewResult.REQUEST_CHANGES,
            blocking_findings=("CP-C04",),
            dependency_states={"TASK-0007": TaskStatus.REVIEW},
        )

        with self.assertRaises(CompletionGateError) as caught:
            self.machine.transition(task, TaskStatus.DONE, context)

        message = str(caught.exception)
        self.assertIn("incomplete acceptance criteria", message)
        self.assertIn("tests have not passed", message)
        self.assertIn("Reviewer result is not APPROVE", message)
        self.assertIn("blocking findings remain", message)
        self.assertIn("dependencies are not DONE", message)
        self.assertIn("completion evidence is missing", message)

    def test_missing_dependency_state_blocks_done(self) -> None:
        task = task_in(
            TaskStatus.REVIEW,
            criteria_complete=True,
            dependencies=("TASK-0007",),
        )
        with self.assertRaises(CompletionGateError) as caught:
            self.machine.transition(
                task,
                TaskStatus.DONE,
                approved_context(dependency_states={}),
            )
        self.assertIn("TASK-0007", str(caught.exception))

    def test_transition_metadata_is_required(self) -> None:
        task = task_in(TaskStatus.TODO)
        with self.assertRaises(TransitionValidationError):
            self.machine.transition(
                task,
                TaskStatus.IN_PROGRESS,
                TransitionContext(actor=" ", reason="start"),
            )
        with self.assertRaises(TransitionValidationError):
            self.machine.transition(
                task,
                TaskStatus.IN_PROGRESS,
                TransitionContext(actor="Developer", reason=" "),
            )

    def test_naive_timestamp_is_rejected(self) -> None:
        with self.assertRaises(TransitionValidationError):
            self.machine.transition(
                task_in(TaskStatus.TODO),
                TaskStatus.IN_PROGRESS,
                TransitionContext(actor="Developer", reason="start"),
                occurred_at=datetime(2026, 9, 14),
            )

    def test_explicit_timestamp_is_preserved(self) -> None:
        timestamp = datetime(2026, 9, 14, tzinfo=timezone.utc)
        _, event = self.machine.transition(
            task_in(TaskStatus.TODO),
            TaskStatus.IN_PROGRESS,
            TransitionContext(actor="Developer", reason="start"),
            occurred_at=timestamp,
        )
        self.assertEqual(event.timestamp, timestamp)

    def test_existing_evidence_is_deduplicated(self) -> None:
        task = replace(
            task_in(TaskStatus.REVIEW, criteria_complete=True),
            completion_evidence=("CI-123",),
        )
        updated, _ = self.machine.transition(
            task,
            TaskStatus.DONE,
            approved_context(evidence=("CI-123", "PR-10")),
        )
        self.assertEqual(updated.completion_evidence, ("CI-123", "PR-10"))


if __name__ == "__main__":
    unittest.main()
