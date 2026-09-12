"""Tests for the Control Plane Loader."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ai_os.governance import (
    build_authority_map,
    load_control_plane,
    validate_required_files,
)
from ai_os.governance.errors import MissingControlPlaneFileError


FIXTURE_ROOT = (
    Path(__file__).parent
    / "fixtures"
    / "valid_control_plane"
)


class ControlPlaneLoaderTests(unittest.TestCase):
    def test_load_valid_control_plane(self) -> None:
        control_plane = load_control_plane(FIXTURE_ROOT)

        self.assertEqual(len(control_plane.documents), 6)
        self.assertIn("Controller", control_plane.agents)
        self.assertIn("Planner", control_plane.agents)
        self.assertIn("RULE-GEN-001", control_plane.rules)
        self.assertIn("REVIEW", control_plane.workflow.states)
        self.assertIn("TASK-0001", control_plane.tasks)
        self.assertEqual(
            control_plane.authority_map["Governance"].document,
            "CONTROL_PLANE.md",
        )
        self.assertEqual(control_plane.warnings, ())

    def test_authority_model_accepts_numbered_level_one_heading(self) -> None:
        markdown = """\
# CONTROL_PLANE.md

# 4. Authority Model

| Decision Domain | Authoritative Document |
|---|---|
| Governance | `CONTROL_PLANE.md` |

# 5. Operating Modes
        """

        authority_map = build_authority_map(markdown)

        self.assertEqual(
            authority_map["Governance"].document,
            "CONTROL_PLANE.md",
        )

    def test_validation_reports_all_missing_files(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaises(
                MissingControlPlaneFileError
            ) as context:
                validate_required_files(directory)

        message = str(context.exception)
        self.assertIn("CONTROL_PLANE.md", message)
        self.assertIn("AGENTS.md", message)
        self.assertIn("TASKS.md", message)


if __name__ == "__main__":
    unittest.main()
