"""Default-deny authority policy derived from AGENTS.md."""

from __future__ import annotations

from .errors import PermissionDeniedError
from .models import AgentRole, Permission

_ROLE_PERMISSIONS: dict[AgentRole, frozenset[Permission]] = {
    AgentRole.CONTROLLER: frozenset({
        Permission.READ_CONTROL, Permission.PROPOSE_CHANGE,
        Permission.UPDATE_TASK_STATUS, Permission.COORDINATE,
        Permission.COMPLETE_TASK,
    }),
    AgentRole.PLANNER: frozenset({
        Permission.READ_CONTROL, Permission.PROPOSE_CHANGE,
        Permission.UPDATE_TASK_STATUS,
    }),
    AgentRole.RESEARCHER: frozenset({
        Permission.READ_CONTROL, Permission.PROPOSE_CHANGE,
    }),
    AgentRole.DEVELOPER: frozenset({
        Permission.READ_CONTROL, Permission.PROPOSE_CHANGE,
        Permission.MODIFY_CODE, Permission.UPDATE_TASK_STATUS,
    }),
    AgentRole.TESTER: frozenset({
        Permission.READ_CONTROL, Permission.PROPOSE_CHANGE,
        Permission.UPDATE_TASK_STATUS,
    }),
    AgentRole.REVIEWER: frozenset({
        Permission.READ_CONTROL, Permission.PROPOSE_CHANGE,
        Permission.UPDATE_TASK_STATUS, Permission.APPROVE_REVIEW,
    }),
    AgentRole.FIXER: frozenset({
        Permission.READ_CONTROL, Permission.PROPOSE_CHANGE,
        Permission.MODIFY_CODE, Permission.UPDATE_TASK_STATUS,
    }),
}


class PermissionPolicy:
    """Authorize only permissions explicitly granted to a canonical role."""

    def permissions_for(self, role: AgentRole) -> frozenset[Permission]:
        return _ROLE_PERMISSIONS.get(role, frozenset())

    def allows(self, role: AgentRole, permission: Permission) -> bool:
        return permission in self.permissions_for(role)

    def require(self, role: AgentRole, permission: Permission) -> None:
        if not self.allows(role, permission):
            raise PermissionDeniedError(
                f"{role.value} is not authorized for {permission.value}"
            )
