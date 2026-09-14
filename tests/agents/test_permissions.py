import unittest

from ai_os.agents import (
    AgentRole, Permission, PermissionDeniedError, PermissionPolicy,
)


class PermissionPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = PermissionPolicy()

    def test_developer_may_modify_code_but_not_control_files(self) -> None:
        self.assertTrue(
            self.policy.allows(AgentRole.DEVELOPER, Permission.MODIFY_CODE)
        )
        self.assertFalse(
            self.policy.allows(AgentRole.DEVELOPER, Permission.MODIFY_CONTROL)
        )

    def test_fixer_cannot_complete_task(self) -> None:
        with self.assertRaises(PermissionDeniedError):
            self.policy.require(AgentRole.FIXER, Permission.COMPLETE_TASK)

    def test_undeclared_permission_is_default_denied_for_every_role(self) -> None:
        for role in AgentRole:
            self.assertFalse(
                self.policy.allows(role, Permission.MODIFY_CONTROL),
                role.value,
            )

    def test_only_reviewer_may_approve_review(self) -> None:
        permitted = [
            role for role in AgentRole
            if self.policy.allows(role, Permission.APPROVE_REVIEW)
        ]
        self.assertEqual(permitted, [AgentRole.REVIEWER])


if __name__ == "__main__":
    unittest.main()
