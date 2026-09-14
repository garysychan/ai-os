import unittest

from ai_os.agents import AgentRole, Capability, canonical_agents


class CanonicalRoleTests(unittest.TestCase):
    def test_each_role_has_one_distinct_canonical_capability(self) -> None:
        agents = canonical_agents()
        self.assertEqual(len(agents), 7)
        self.assertEqual(
            {agent.descriptor.role for agent in agents},
            set(AgentRole),
        )
        self.assertEqual(
            {next(iter(agent.descriptor.capabilities)) for agent in agents},
            set(Capability),
        )

    def test_descriptors_contain_permissions_and_descriptions(self) -> None:
        for agent in canonical_agents():
            self.assertTrue(agent.descriptor.permissions)
            self.assertTrue(agent.descriptor.description)


if __name__ == "__main__":
    unittest.main()
