"""Default-deny execution policy."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from ai_os.agents import PermissionPolicy
from ai_os.tasks import Task, TaskStatus, validate_task

from .errors import ExecutionPolicyError, ExecutionValidationError
from .models import ExecutionContext, ExecutionPlan, ExecutionStep
from .ports import ExecutionAdapter


class ExecutionPolicy:
    def __init__(self, permission_policy: PermissionPolicy | None = None) -> None:
        self.permission_policy = permission_policy or PermissionPolicy()

    def validate_start(
        self,
        task: Task,
        plan: ExecutionPlan,
        context: ExecutionContext,
        dependency_states: Mapping[str, TaskStatus],
        now: datetime,
    ) -> None:
        validate_task(task)
        if task.status is not TaskStatus.IN_PROGRESS:
            raise ExecutionPolicyError("Execution Engine requires an IN_PROGRESS task")
        if plan.task_id != task.task_id:
            raise ExecutionValidationError("plan task_id does not match Task")
        if not plan.plan_id.strip() or not context.controller_session_id.strip():
            raise ExecutionValidationError("plan and Controller session IDs must not be empty")
        if not context.objective.strip():
            raise ExecutionValidationError("execution objective must not be empty")
        if now.tzinfo is None or now.utcoffset() is None:
            raise ExecutionValidationError("execution timestamp must be timezone-aware")
        if context.deadline is not None:
            if context.deadline.tzinfo is None or context.deadline.utcoffset() is None:
                raise ExecutionValidationError("execution deadline must be timezone-aware")
            if now >= context.deadline:
                raise ExecutionPolicyError("execution deadline has expired")
        unfinished = [
            item for item in task.dependencies if dependency_states.get(item) is not TaskStatus.DONE
        ]
        if unfinished:
            raise ExecutionPolicyError("dependencies are not DONE: " + ", ".join(unfinished))
        if plan.max_steps <= 0:
            raise ExecutionValidationError("max_steps must be positive")
        if not plan.steps:
            raise ExecutionValidationError("execution plan must contain at least one step")
        if len(plan.steps) > plan.max_steps:
            raise ExecutionPolicyError("execution plan exceeds finite step budget")
        identifiers = [step.step_id for step in plan.steps]
        if len(identifiers) != len(set(identifiers)):
            raise ExecutionValidationError("execution step IDs must be unique")
        for step in plan.steps:
            self.validate_step(task, step)

    def validate_step(self, task: Task, step: ExecutionStep) -> None:
        if not step.step_id.strip() or not step.adapter.strip() or not step.operation.strip():
            raise ExecutionValidationError("step ID, adapter, and operation must not be empty")
        if step.agent_role.value not in task.agents:
            raise ExecutionPolicyError(f"{step.agent_role.value} is not assigned to {task.task_id}")
        try:
            self.permission_policy.require(step.agent_role, step.required_permission)
        except Exception as error:
            raise ExecutionPolicyError(str(error)) from error
        if step.max_retries < 0:
            raise ExecutionValidationError("max_retries must not be negative")
        if not step.idempotent and step.max_retries:
            raise ExecutionPolicyError("non-idempotent steps cannot be retried")

    @staticmethod
    def validate_adapter(adapter: ExecutionAdapter) -> None:
        if adapter.has_external_side_effects:
            raise ExecutionPolicyError("external side-effect adapters are not authorized")
