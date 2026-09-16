"""Default-deny Adapter invocation policy."""

from datetime import datetime

from ai_os.agents import PermissionDeniedError, PermissionPolicy
from ai_os.agents.permissions import CAPABILITY_PERMISSION
from ai_os.tasks import Task, TaskStatus, validate_task

from .errors import AdapterPolicyError
from .models import AdapterInvocation, AdapterMetadata, SideEffect
from .validation import validate_invocation, validate_metadata


class AdapterPolicy:
    def __init__(self, permission_policy: PermissionPolicy | None = None) -> None:
        self.permission_policy = permission_policy or PermissionPolicy()

    def authorize(
        self,
        task: Task,
        metadata: AdapterMetadata,
        invocation: AdapterInvocation,
        now: datetime,
    ) -> None:
        validate_task(task)
        validate_metadata(metadata)
        validate_invocation(invocation, now)
        if task.status is not TaskStatus.IN_PROGRESS:
            raise AdapterPolicyError("Adapters require an IN_PROGRESS task")
        if invocation.task_id != task.task_id:
            raise AdapterPolicyError("invocation task_id does not match Task")
        if invocation.agent_role.value not in task.agents:
            raise AdapterPolicyError(f"{invocation.agent_role.value} is not assigned to task")
        canonical = CAPABILITY_PERMISSION[invocation.capability]
        if invocation.required_permission is not canonical:
            raise AdapterPolicyError(
                f"capability {invocation.capability.value} requires {canonical.value}"
            )
        try:
            self.permission_policy.require(invocation.agent_role, canonical)
        except PermissionDeniedError as error:
            raise AdapterPolicyError(str(error)) from error
        if (invocation.adapter, invocation.version) != (metadata.name, metadata.version):
            raise AdapterPolicyError("invocation does not match resolved Adapter")
        if invocation.operation not in metadata.operations:
            raise AdapterPolicyError("operation is not declared by Adapter")
        if (
            invocation.max_attempts > 1
            and invocation.operation not in metadata.idempotent_operations
        ):
            raise AdapterPolicyError("non-idempotent Adapter operations cannot be retried")
        if metadata.side_effect is SideEffect.WRITE_EXTERNAL:
            raise AdapterPolicyError("write-capable Adapters are not authorized")
