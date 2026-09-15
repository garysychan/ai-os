"""CLI tests for Controller dry-run and process-local session inspection."""

import io
import json
import shutil
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from ai_os.cli import _SESSION_STORE, main


class ControllerCliTests(unittest.TestCase):
    def setUp(self) -> None:
        _SESSION_STORE.clear()

    def run_cli(self, *args: str) -> tuple[int, dict[str, object]]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(list(args))
        return code, json.loads(output.getvalue())

    def test_dry_run_can_be_shown_and_traced(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (
                "CONTROL_PLANE.md",
                "AGENTS.md",
                "PROJECT_RULES.md",
                "ARCHITECTURE.md",
                "WORKFLOW.md",
                "TASKS.md",
            ):
                shutil.copy(name, root / name)
            tasks = (root / "TASKS.md").read_text(encoding="utf-8")
            tasks = tasks.replace(
                "## TASK-0010 — Install Controller Orchestration Engine\n\n"
                "Priority: P1  \nAgent: Controller / Developer / Tester / Reviewer  \n"
                "Status: REVIEW",
                "## TASK-0010 — Install Controller Orchestration Engine\n\n"
                "Priority: P1  \nAgent: Controller / Developer / Tester / Reviewer  \n"
                "Status: IN_PROGRESS",
            )
            (root / "TASKS.md").write_text(tasks, encoding="utf-8")
            code, payload = self.run_cli(
                "run",
                "TASK-0010",
                "--objective",
                "inspect lifecycle",
                "--root",
                str(root),
                "--dry-run",
                "--json",
            )
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "PASS")
        session_id = str(payload["session_id"])

        show_code, shown = self.run_cli("session", "show", session_id, "--json")
        trace_code, trace = self.run_cli("session", "trace", session_id, "--json")
        self.assertEqual((show_code, trace_code), (0, 0))
        self.assertEqual(shown["task_id"], "TASK-0010")
        self.assertEqual(len(trace["events"]), 1)

    def test_unknown_session_fails(self) -> None:
        code, payload = self.run_cli("session", "show", "missing", "--json")
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
