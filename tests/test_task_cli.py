"""Tests for Task Schema and transition CLI commands."""

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ai_os.cli import main


FIXTURE_TASKS = (
    Path(__file__).parent
    / "fixtures"
    / "valid_control_plane"
    / "TASKS.md"
)


class TaskCliTests(unittest.TestCase):
    def run_json(self, arguments: list[str]) -> tuple[int, dict[str, object]]:
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main([*arguments, "--json"])
        return exit_code, json.loads(output.getvalue())

    def test_task_validate_accepts_fixture(self) -> None:
        exit_code, payload = self.run_json(
            ["task", "validate", str(FIXTURE_TASKS)]
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["operation"], "TASK SCHEMA VALIDATION")
        self.assertEqual(len(payload["tasks"]), 1)

    def test_task_validate_reports_missing_file(self) -> None:
        exit_code, payload = self.run_json(
            ["task", "validate", "does-not-exist.md"]
        )

        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["error_type"], "FileNotFoundError")

    def test_task_validate_rejects_invalid_priority(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "TASKS.md"
            path.write_text(
                """# TASKS.md

## TASK-0010 — Invalid Priority

Priority: PX
Agent: Developer
Status: TODO
Dependencies: None

Acceptance Criteria:
- [ ] Rejected.
""",
                encoding="utf-8",
            )
            exit_code, payload = self.run_json(
                ["task", "validate", str(path)]
            )

        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["error_type"], "ValueError")

    def test_task_transitions_lists_policy(self) -> None:
        exit_code, payload = self.run_json(["task", "transitions"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "PASS")
        transitions = payload["transitions"]
        self.assertEqual(len(transitions), 9)
        self.assertIn(
            {"from": "REVIEW", "to": "DONE"},
            transitions,
        )
        self.assertNotIn(
            {"from": "TODO", "to": "DONE"},
            transitions,
        )

    def test_human_reports_are_available(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            validate_code = main(
                ["task", "validate", str(FIXTURE_TASKS)]
            )
            transitions_code = main(["task", "transitions"])

        report = output.getvalue()
        self.assertEqual(validate_code, 0)
        self.assertEqual(transitions_code, 0)
        self.assertIn("TASK SCHEMA VALIDATION", report)
        self.assertIn("TASK STATE TRANSITIONS", report)
        self.assertIn("Status: PASS", report)


if __name__ == "__main__":
    unittest.main()
