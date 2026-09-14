"""Tests for immutable Task domain models."""

from dataclasses import FrozenInstanceError
import unittest

from ai_os.tasks import (
    AcceptanceCriterion,
    Priority,
    ReviewResult,
    Task,
    TaskStatus,
)


class TaskModelTests(unittest.TestCase):
    def test_enum_values_match_control_plane(self) -> None:
        self.assertEqual(TaskStatus.TODO.value, "TODO")
        self.assertEqual(TaskStatus.IN_PROGRESS.value, "IN_PROGRESS")
        self.assertEqual(TaskStatus.BLOCKED.value, "BLOCKED")
        self.assertEqual(TaskStatus.REVIEW.value, "REVIEW")
        self.assertEqual(TaskStatus.DONE.value, "DONE")
        self.assertEqual([item.value for item in Priority], ["P0", "P1", "P2", "P3"])
        self.assertEqual(ReviewResult.APPROVE.value, "APPROVE")

    def test_task_and_criterion_are_immutable(self) -> None:
        criterion = AcceptanceCriterion("Tests pass")
        task = Task(
            task_id="TASK-0010",
            title="Task Schema",
            priority=Priority.P1,
            status=TaskStatus.TODO,
            agents=("Developer",),
            dependencies=("TASK-0007",),
            acceptance_criteria=(criterion,),
            metadata=(("cr", "CR-2026-005"),),
        )

        with self.assertRaises(FrozenInstanceError):
            task.status = TaskStatus.DONE  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            criterion.completed = True  # type: ignore[misc]

        self.assertIsInstance(task.metadata, tuple)


if __name__ == "__main__":
    unittest.main()
