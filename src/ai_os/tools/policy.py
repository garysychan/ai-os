"""Authority-preserving Tool invocation policy."""

from ai_os.adapters import SideEffect
from ai_os.agents import PermissionDeniedError, PermissionPolicy
from ai_os.tasks import Task, TaskStatus, validate_task

from .errors import ToolPolicyError
from .models import ToolInvocation, ToolOperation
from .validation import validate_invocation


class ToolPolicy:
    def __init__(self, permission_policy: PermissionPolicy | None = None) -> None:
        self.permission_policy = permission_policy or PermissionPolicy()

    def authorize(
        self,
        task: Task,
        operation: ToolOperation,
        invocation: ToolInvocation,
    ) -> None:
        validate_task(task)
        validate_invocation(invocation)
        if task.status is not TaskStatus.IN_PROGRESS:
            raise ToolPolicyError("Tools require an IN_PROGRESS task")
        if invocation.task_id != task.task_id:
            raise ToolPolicyError("Tool invocation task_id does not match Task")
        if invocation.agent_role.value not in task.agents:
            raise ToolPolicyError(f"{invocation.agent_role.value} is not assigned to task")
        if invocation.capability is not operation.capability:
            raise ToolPolicyError("Tool invocation capability does not match operation")
        if invocation.required_permission is not operation.required_permission:
            raise ToolPolicyError("Tool invocation permission does not match operation")
        try:
            self.permission_policy.require(invocation.agent_role, invocation.required_permission)
        except PermissionDeniedError as error:
            raise ToolPolicyError(str(error)) from error
        if operation.approval_required and not invocation.approval_evidence:
            raise ToolPolicyError("Tool operation requires explicit approval evidence")
        if operation.side_effect is SideEffect.WRITE_EXTERNAL:
            raise ToolPolicyError("write-capable Tools are not authorized")
        if invocation.max_attempts > 1 and not operation.idempotent:
            raise ToolPolicyError("non-idempotent Tool operations cannot be retried")
