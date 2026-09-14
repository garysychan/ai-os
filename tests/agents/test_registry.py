import unittest

from ai_os.agents import (
    AgentNotFoundError, AgentRegistry, AgentRole, CanonicalAgent,
    DuplicateAgentError, canonical_agents,
)


class RegistryTests(unittest.TestCase):
    def test_register_lookup_and_deterministic_list(self) -> None:
        registry = AgentRegistry(canonical_agents())
        self.assertEqual(
            registry.get(AgentRole.REVIEWER).descriptor.role,
            AgentRole.REVIEWER,
        )
        names = [agent.descriptor.role.value for agent in registry.list()]
        self.assertEqual(names, sorted(names))

    def test_duplicate_role_is_rejected(self) -> None:
        agent = CanonicalAgent(AgentRole.DEVELOPER)
        registry = AgentRegistry([agent])
        with self.assertRaises(DuplicateAgentError):
            registry.register(agent)

    def test_missing_role_is_explicit(self) -> None:
        with self.assertRaises(AgentNotFoundError):
            AgentRegistry().get(AgentRole.TESTER)


if __name__ == "__main__":
    unittest.main()
