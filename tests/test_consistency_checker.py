"""Tests for CP-C01 through CP-C10 consistency checks."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import unittest

from ai_os.governance import (
    Severity,
    load_control_plane,
    run_consistency_checks,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "valid_control_plane"


class ConsistencyCheckerTests(unittest.TestCase):
    def _copy_fixture(self, directory: str) -> Path:
        root = Path(directory)
        for source in FIXTURE_ROOT.iterdir():
            shutil.copy2(source, root / source.name)
        return root

    def test_all_check_ids_are_reported_by_schema(self) -> None:
        control_plane = load_control_plane(FIXTURE_ROOT)
        report = run_consistency_checks(control_plane)

        payload = report.to_dict()

        self.assertEqual(
            payload["checks"],
            [f"CP-C{number:02d}" for number in range(1, 11)],
        )
        self.assertNotEqual(report.status, "FAIL")

    def test_dependency_cycle_is_blocking(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._copy_fixture(directory)
            tasks = root / "TASKS.md"
            tasks.write_text(
                tasks.read_text(encoding="utf-8")
                + """
## TASK-0002 — Second Task

Priority: P1
Agent: Planner
Status: TODO
Dependencies: TASK-0003

Acceptance Criteria:
- [ ] Second task complete.

## TASK-0003 — Third Task

Priority: P1
Agent: Planner
Status: TODO
Dependencies: TASK-0002

Acceptance Criteria:
- [ ] Third task complete.
""",
                encoding="utf-8",
            )
            report = run_consistency_checks(load_control_plane(root))

        cycles = [
            finding
            for finding in report.findings_for("CP-C07")
            if "cycle" in finding.message.casefold()
        ]
        self.assertEqual(report.status, "FAIL")
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0].severity, Severity.FAIL)

    def test_unauthorized_control_file_permission_is_blocking(self) -> None:
        with TemporaryDirectory() as directory:
            root = self._copy_fixture(directory)
            agents = root / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8")
                + """
## 4. Permission Model

| Agent | Modify Control Files |
|---|---:|
| Controller | Yes |
""",
                encoding="utf-8",
            )
            report = run_consistency_checks(load_control_plane(root))

        findings = report.findings_for("CP-C08")
        self.assertEqual(report.status, "FAIL")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].subject, "Controller")

    def test_missing_version_metadata_is_non_blocking(self) -> None:
        report = run_consistency_checks(load_control_plane(FIXTURE_ROOT))

        findings = report.findings_for("CP-C09")

        self.assertTrue(findings)
        self.assertTrue(
            all(item.severity is Severity.WARNING for item in findings)
        )
        self.assertEqual(report.status, "WARNING")


if __name__ == "__main__":
    unittest.main()
