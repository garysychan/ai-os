"""Reviewer-requested regression tests for CR-2026-003."""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

from ai_os.cli import main
from ai_os.governance import (
    is_valid_transition,
    load_control_plane,
    run_consistency_checks,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "valid_control_plane"


class ConsistencyFixCycleTests(unittest.TestCase):
    def _copy_fixture(self, directory: str) -> Path:
        root = Path(directory)
        for source in FIXTURE_ROOT.iterdir():
            shutil.copy2(source, root / source.name)
        return root

    def test_missing_files_use_cp_c01_report_schema(self) -> None:
        with TemporaryDirectory() as directory:
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "control-plane",
                        "check",
                        "--root",
                        directory,
                        "--json",
                    ]
                )

        payload = json.loads(output.getvalue())
        finding = payload["consistency"]["findings"][0]
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(finding["check_id"], "CP-C01")

    def test_permission_table_cannot_reference_unknown_agent(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._copy_fixture(directory)
            agents = root / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8")
                + """
## 4. Permission Model

| Agent | Modify Control Files |
|---|---:|
| Controller | No |
| Planner | No |
| Ghost | No |
""",
                encoding="utf-8",
            )
            report = run_consistency_checks(load_control_plane(root))

        findings = report.findings_for("CP-C03")
        self.assertTrue(
            any(
                item.subject == "ghost" and item.severity.name == "FAIL"
                for item in findings
            )
        )

    def test_executable_transition_policy_rejects_bypass(self) -> None:
        self.assertTrue(is_valid_transition("TODO", "IN_PROGRESS"))
        self.assertTrue(is_valid_transition("REVIEW", "DONE"))
        self.assertFalse(is_valid_transition("TODO", "DONE"))
        self.assertFalse(is_valid_transition("DONE", "IN_PROGRESS"))

    def test_declared_illegal_transition_fails_cp_c04(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._copy_fixture(directory)
            workflow = root / "WORKFLOW.md"
            workflow.write_text(
                workflow.read_text(encoding="utf-8")
                + "\nTODO -> DONE\n",
                encoding="utf-8",
            )
            report = run_consistency_checks(load_control_plane(root))

        findings = report.findings_for("CP-C04")
        self.assertTrue(
            any(
                item.subject == "TODO -> DONE"
                and item.severity.name == "FAIL"
                for item in findings
            )
        )

    def test_architecture_state_mismatch_fails_cp_c05(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._copy_fixture(directory)
            architecture = root / "ARCHITECTURE.md"
            architecture.write_text(
                architecture.read_text(encoding="utf-8")
                + "\nStates: TODO, DONE\n",
                encoding="utf-8",
            )
            report = run_consistency_checks(load_control_plane(root))

        self.assertTrue(
            any(
                item.severity.name == "FAIL"
                for item in report.findings_for("CP-C05")
            )
        )

    def test_opposite_rule_propositions_fail_cp_c06(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._copy_fixture(directory)
            (root / "PROJECT_RULES.md").write_text(
                """# PROJECT_RULES.md

- **RULE-AI-001:** Agents must execute tasks.
- **RULE-AI-002:** Agents must not execute tasks.
""",
                encoding="utf-8",
            )
            report = run_consistency_checks(load_control_plane(root))

        self.assertTrue(
            any(
                item.severity.name == "FAIL"
                for item in report.findings_for("CP-C06")
            )
        )

    def test_unused_agent_is_reported_by_cp_c10(self) -> None:
        report = run_consistency_checks(load_control_plane(FIXTURE_ROOT))

        self.assertTrue(
            any(
                item.subject == "Planner"
                for item in report.findings_for("CP-C10")
            )
        )


if __name__ == "__main__":
    unittest.main()
