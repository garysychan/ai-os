"""Governed Tool facade that always delegates execution to AdapterService."""

from collections.abc import Callable
from datetime import datetime

from ai_os.adapters import AdapterInvocation, AdapterService
from ai_os.tasks import Task

from .models import ToolInvocation, ToolResult
from .policy import ToolPolicy
from .registry import ToolRegistry


class ToolService:
    def __init__(
        self,
        registry: ToolRegistry,
        adapter_service: AdapterService,
        policy: ToolPolicy | None = None,
    ) -> None:
        if adapter_service.registry is not registry.adapter_registry:
            raise ValueError("ToolRegistry and AdapterService must share one AdapterRegistry")
        self.registry = registry
        self.adapter_service = adapter_service
        self.policy = policy or ToolPolicy()

    def execute(
        self,
        task: Task,
        invocation: ToolInvocation,
        *,
        clock: Callable[[], datetime] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> ToolResult:
        operation = self.registry.resolve_operation(
            invocation.tool, invocation.version, invocation.operation
        )
        self.policy.authorize(task, operation, invocation)
        adapter_invocation = AdapterInvocation(
            invocation_id=invocation.invocation_id,
            task_id=invocation.task_id,
            adapter=operation.adapter,
            version=operation.adapter_version,
            operation=operation.adapter_operation,
            agent_role=invocation.agent_role,
            capability=invocation.capability,
            required_permission=invocation.required_permission,
            inputs=invocation.inputs,
            attempt=invocation.attempt,
            max_attempts=invocation.max_attempts,
        )
        result, audit = self.adapter_service.execute(
            task, adapter_invocation, clock=clock, cancelled=cancelled
        )
        return ToolResult(
            invocation.tool,
            invocation.version,
            invocation.operation,
            result,
            audit,
        )
