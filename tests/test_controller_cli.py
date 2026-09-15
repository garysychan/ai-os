"""CLI tests for Controller dry-run and process-local session inspection."""

import io
import json
import unittest
from contextlib import redirect_stdout

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
        code, payload = self.run_cli(
            "run",
            "TASK-0010",
            "--objective",
            "inspect lifecycle",
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
