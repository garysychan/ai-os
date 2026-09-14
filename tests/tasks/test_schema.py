"""Tests for Task Schema validation."""

import unittest

from ai_os.tasks import (
    AcceptanceCriterion,
    Priority,
    Task,
    TaskStatus,
    TaskValidationError,
    validate_task,
    validation_issues,
)


def valid_task(**changes: object) -> Task:
    values: dict[str, object] = {
        "task_id": "TASK-0010",
        "title": "Install Task Schema",
        "priority": Priority.P1,
        "status": TaskStatus.TODO,
        "agents": ("Developer",),
        "dependencies": ("TASK-0007",),
        "acceptance_criteria": (AcceptanceCriterion("Tests pass"),),
    }
    values.update(changes)
    return Task(**values)  # type: ignore[arg-type]


class TaskSchemaTests(unittest.TestCase):
    def test_valid_task_is_returned(self) -> None:
        task = valid_task()
        self.assertIs(validate_task(task), task)
        self.assertEqual(validation_issues(task), ())

    def test_reports_all_schema_violations(self) -> None:
        task = valid_task(
            task_id="bad",
            title=" ",
            priority="P1",
            status="TODO",
            agents=("",),
            dependencies=("bad", "bad"),
            acceptance_criteria=(AcceptanceCriterion(" "),),
        )

        with self.assertRaises(TaskValidationError) as context:
            validate_task(task)

        message = str(context.exception)
        self.assertIn("priority must be a Priority enum", message)
        self.assertIn("status must be a TaskStatus enum", message)
        self.assertIn("task_id must match", message)
        self.assertIn("title must not be empty", message)
        self.assertIn("Agent names must not be empty", message)
        self.assertIn("dependencies must not contain duplicates", message)
        self.assertIn("description must not be empty", message)

    def test_rejects_self_dependency(self) -> None:
        task = valid_task(dependencies=("TASK-0010",))
        self.assertIn(
            "a Task cannot depend on itself",
            validation_issues(task),
        )

    def test_done_task_requires_completion_evidence(self) -> None:
        task = valid_task(status=TaskStatus.DONE)
        self.assertIn(
            "a DONE Task must include completion_evidence",
            validation_issues(task),
        )

    def test_done_task_with_evidence_is_valid(self) -> None:
        task = valid_task(
            status=TaskStatus.DONE,
            completion_evidence=("CI-123",),
        )
        self.assertIs(validate_task(task), task)


if __name__ == "__main__":
    unittest.main()
