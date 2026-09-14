"""Tests for the executable transition policy."""

import unittest

from ai_os.tasks import TaskStatus
from ai_os.workflow import (
    ALLOWED_TRANSITIONS,
    is_valid_transition,
    normalize_status,
)


class TransitionPolicyTests(unittest.TestCase):
    def test_all_approved_transitions_are_available(self) -> None:
        expected = {
            (TaskStatus.TODO, TaskStatus.IN_PROGRESS),
            (TaskStatus.TODO, TaskStatus.BLOCKED),
            (TaskStatus.IN_PROGRESS, TaskStatus.REVIEW),
            (TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED),
            (TaskStatus.REVIEW, TaskStatus.IN_PROGRESS),
            (TaskStatus.REVIEW, TaskStatus.BLOCKED),
            (TaskStatus.REVIEW, TaskStatus.DONE),
            (TaskStatus.BLOCKED, TaskStatus.TODO),
            (TaskStatus.BLOCKED, TaskStatus.IN_PROGRESS),
        }
        self.assertEqual(ALLOWED_TRANSITIONS, frozenset(expected))
        for source, target in expected:
            self.assertTrue(is_valid_transition(source, target))

    def test_bypass_transitions_are_rejected(self) -> None:
        prohibited = (
            ("TODO", "DONE"),
            ("IN_PROGRESS", "DONE"),
            ("DONE", "TODO"),
            ("DONE", "IN_PROGRESS"),
        )
        for source, target in prohibited:
            with self.subTest(source=source, target=target):
                self.assertFalse(is_valid_transition(source, target))

    def test_unknown_state_is_rejected(self) -> None:
        self.assertFalse(is_valid_transition("UNKNOWN", "TODO"))

    def test_normalize_status_accepts_enum_and_exact_string(self) -> None:
        self.assertIs(
            normalize_status(TaskStatus.REVIEW),
            TaskStatus.REVIEW,
        )
        self.assertIs(normalize_status("REVIEW"), TaskStatus.REVIEW)

    def test_governance_api_remains_string_compatible(self) -> None:
        from ai_os.governance import ALLOWED_TRANSITIONS as legacy
        from ai_os.governance import is_valid_transition as legacy_valid

        self.assertIn(("TODO", "IN_PROGRESS"), legacy)
        self.assertTrue(legacy_valid("TODO", "IN_PROGRESS"))


if __name__ == "__main__":
    unittest.main()
