from dataclasses import FrozenInstanceError
import unittest

from ai_os.agents import AgentRole, Capability, ExecutionStatus
from ai_os.agents.models import AgentDescriptor
from ai_os.tasks import TaskStatus


class AgentModelTests(unittest.TestCase):
    def test_all_canonical_roles_exist(self) -> None:
        self.assertEqual(
            {role.value for role in AgentRole},
            {"Controller", "Planner", "Researcher", "Developer",
             "Tester", "Reviewer", "Fixer"},
        )

    def test_descriptor_is_immutable(self) -> None:
        descriptor = AgentDescriptor(
            AgentRole.PLANNER, frozenset({Capability.PLAN}),
            frozenset(), frozenset({TaskStatus.IN_PROGRESS}), "Plans work",
        )
        with self.assertRaises(FrozenInstanceError):
            descriptor.description = "changed"  # type: ignore[misc]

    def test_execution_statuses_are_explicit(self) -> None:
        self.assertEqual(
            {item.value for item in ExecutionStatus},
            {"SUCCESS", "BLOCKED", "FAILED", "ESCALATED"},
        )


if __name__ == "__main__":
    unittest.main()
