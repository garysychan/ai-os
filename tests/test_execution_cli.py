"""CLI tests for Execution Engine validation, dry-run, and inspection."""

import io
import json
import re
import shutil
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from ai_os.cli import _EXECUTION_STORE, main


class ExecutionCliTests(unittest.TestCase):
    def setUp(self) -> None:
        _EXECUTION_STORE.clear()

    def run_cli(self, *args: str) -> tuple[int, dict[str, object]]:
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(list(args))
        return code, json.loads(output.getvalue())

    def fixture(self, directory: str) -> tuple[Path, Path]:
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
        tasks, replacements = re.subn(
            r"(## TASK-0011\b.*?\nStatus:)\s*"
            r"(?:TODO|IN_PROGRESS|BLOCKED|REVIEW|DONE)(?=\s*\nDependencies:)",
            r"\1 IN_PROGRESS",
            tasks,
            count=1,
            flags=re.DOTALL,
        )
        self.assertEqual(replacements, 1)
        (root / "TASKS.md").write_text(tasks, encoding="utf-8")
        plan = root / "plan.json"
        plan.write_text(
            json.dumps(
                {
                    "plan_id": "cli-plan",
                    "task_id": "TASK-0011",
                    "max_steps": 1,
                    "steps": [
                        {
                            "step_id": "validate",
                            "adapter": "noop",
                            "operation": "record",
                            "agent_role": "Developer",
                            "capability": "implement",
                            "required_permission": "modify_code",
                            "inputs": {"scope": "dry-run"},
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return root, plan

    def test_validate_execute_show_and_trace(self) -> None:
        with TemporaryDirectory() as directory:
            root, plan = self.fixture(directory)
            validate_code, validated = self.run_cli(
                "execution", "validate", str(plan), "--root", str(root), "--json"
            )
            execute_code, executed = self.run_cli(
                "execute",
                "TASK-0011",
                "--plan",
                str(plan),
                "--root",
                str(root),
                "--dry-run",
                "--json",
            )
        self.assertEqual((validate_code, execute_code), (0, 0))
        self.assertEqual(validated["status"], "PASS")
        self.assertEqual(executed["side_effects"], "NONE")
        execution_id = str(executed["execution_id"])
        show_code, shown = self.run_cli("execution", "show", execution_id, "--json")
        trace_code, trace = self.run_cli("execution", "trace", execution_id, "--json")
        self.assertEqual((show_code, trace_code), (0, 0))
        self.assertEqual(shown["outcome"], "COMPLETED")
        self.assertEqual(len(trace["events"]), 4)

    def test_adapters_and_unknown_session(self) -> None:
        code, payload = self.run_cli("execution", "adapters", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(payload["adapters"], ["noop"])
        code, payload = self.run_cli("execution", "show", "missing", "--json")
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
