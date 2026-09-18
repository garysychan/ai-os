"""Default-deny authority policy for Workflow execution."""

from collections.abc import Mapping
from datetime import datetime

from ai_os.agents import PermissionDeniedError, PermissionPolicy
from ai_os.tasks import Task, TaskStatus, validate_task

from .errors import WorkflowPolicyError
from .models import WorkflowDefinition
from .validation import validate_definition


class WorkflowPolicy:
    def __init__(self, permission_policy: PermissionPolicy | None = None) -> None:
        self.permission_policy = permission_policy or PermissionPolicy()

    def authorize(
        self,
        task: Task,
        definition: WorkflowDefinition,
        dependency_states: Mapping[str, TaskStatus],
        *,
        now: datetime,
        deadline: datetime | None,
        approval_evidence: tuple[str, ...],
        max_fix_attempts: int,
    ) -> None:
        validate_task(task)
        validate_definition(definition)
        if task.status is not TaskStatus.IN_PROGRESS:
            raise WorkflowPolicyError("Workflow execution requires an IN_PROGRESS task")
        unfinished = [
            item for item in task.dependencies if dependency_states.get(item) is not TaskStatus.DONE
        ]
        if unfinished:
            raise WorkflowPolicyError("dependencies are not DONE: " + ", ".join(unfinished))
        if now.tzinfo is None or now.utcoffset() is None:
            raise WorkflowPolicyError("Workflow clock must be timezone-aware")
        if deadline is not None:
            if deadline.tzinfo is None or deadline.utcoffset() is None:
                raise WorkflowPolicyError("Workflow deadline must be timezone-aware")
            if now >= deadline:
                raise WorkflowPolicyError("Workflow deadline has expired")
        if max_fix_attempts < 0 or max_fix_attempts > definition.max_fix_attempts:
            raise WorkflowPolicyError("requested Fix Cycle budget exceeds Workflow policy")
        if definition.approval_required and not approval_evidence:
            raise WorkflowPolicyError("Workflow requires explicit approval evidence")
        assigned = set(task.agents)
        for stage in definition.stages:
            if stage.agent_role.value not in assigned:
                raise WorkflowPolicyError(f"{stage.agent_role.value} is not assigned to task")
            try:
                self.permission_policy.require(stage.agent_role, stage.required_permission)
            except PermissionDeniedError as error:
                raise WorkflowPolicyError(str(error)) from error
