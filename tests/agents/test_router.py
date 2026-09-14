import unittest

from ai_os.agents import (
    AgentRegistry, AgentRole, AgentRouter, Capability, ExecutionRequest,
    Permission, PermissionDeniedError, RoutingError, canonical_agents,
)
from ai_os.tasks import AcceptanceCriterion, Priority, Task, TaskStatus


def task() -> Task:
    return Task(
        "TASK-0100", "Implement", Priority.P1, TaskStatus.IN_PROGRESS,
        ("Developer",), (), (AcceptanceCriterion("works"),),
    )


class RouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.router = AgentRouter(AgentRegistry(canonical_agents()))

    def request(self, **changes: object) -> ExecutionRequest:
        values = {
            "task": task(), "capability": Capability.IMPLEMENT,
            "objective": "Implement feature", "actor": "Codex",
        }
        values.update(changes)
        return ExecutionRequest(**values)  # type: ignore[arg-type]

    def test_routes_by_capability_deterministically(self) -> None:
        agent = self.router.route(self.request())
        self.assertEqual(agent.descriptor.role, AgentRole.DEVELOPER)

    def test_requested_incompatible_role_is_rejected(self) -> None:
        with self.assertRaises(RoutingError):
            self.router.route(
                self.request(requested_role=AgentRole.REVIEWER)
            )

    def test_permission_is_checked_before_dispatch(self) -> None:
        with self.assertRaises(PermissionDeniedError):
            self.router.route(
                self.request(required_permission=Permission.MODIFY_CONTROL)
            )


if __name__ == "__main__":
    unittest.main()
