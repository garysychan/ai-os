"""Governed Tool facade that always delegates execution to AdapterService."""

from collections.abc import Callable
from contextlib import suppress
from datetime import datetime

from ai_os.adapters import AdapterInvocation, AdapterService
from ai_os.tasks import Task

from .errors import ToolError
from .models import ToolInvocation, ToolResult
from .policy import ToolPolicy
from .registry import ToolRegistry


class ToolService:
    def __init__(
        self,
        registry: ToolRegistry,
        adapter_service: AdapterService,
        policy: ToolPolicy | None = None,
        audit_sink: Callable[[ToolInvocation, ToolResult], None] | None = None,
        denial_sink: Callable[[ToolInvocation, datetime, str], None] | None = None,
    ) -> None:
        if adapter_service.registry is not registry.adapter_registry:
            raise ValueError("ToolRegistry and AdapterService must share one AdapterRegistry")
        self.registry = registry
        self.adapter_service = adapter_service
        self.policy = policy or ToolPolicy()
        self.audit_sink = audit_sink
        self.denial_sink = denial_sink

    def execute(
        self,
        task: Task,
        invocation: ToolInvocation,
        *,
        clock: Callable[[], datetime] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> ToolResult:
        now = (clock or (lambda: datetime.now().astimezone()))()
        try:
            operation = self.registry.resolve_operation(
                invocation.tool, invocation.version, invocation.operation
            )
            self.policy.authorize(task, operation, invocation)
        except ToolError as error:
            if self.denial_sink is not None:
                with suppress(Exception):
                    self.denial_sink(invocation, now, type(error).__name__)
            raise
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
            deadline=invocation.deadline,
        )
        result, audit = self.adapter_service.execute(
            task, adapter_invocation, clock=(lambda: now), cancelled=cancelled
        )
        tool_result = ToolResult(
            invocation.tool,
            invocation.version,
            invocation.operation,
            result,
            audit,
        )
        if self.audit_sink is not None:
            with suppress(Exception):
                self.audit_sink(invocation, tool_result)
        return tool_result
