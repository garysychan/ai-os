"""Governed Adapter execution facade."""

from collections.abc import Callable
from datetime import UTC, datetime

from ai_os.tasks import Task

from .audit import make_audit_event
from .models import AdapterAuditEvent, AdapterInvocation, AdapterResult
from .policy import AdapterPolicy
from .registry import AdapterRegistry
from .validation import validate_result


class AdapterService:
    def __init__(
        self,
        registry: AdapterRegistry,
        policy: AdapterPolicy | None = None,
        max_output_bytes: int = 1_100_000,
    ) -> None:
        self.registry = registry
        self.policy = policy or AdapterPolicy()
        self.max_output_bytes = max_output_bytes

    def execute(
        self,
        task: Task,
        invocation: AdapterInvocation,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> tuple[AdapterResult, AdapterAuditEvent]:
        now = (clock or (lambda: datetime.now(UTC)))()
        adapter = self.registry.resolve(
            invocation.adapter, invocation.version, invocation.operation
        )
        self.policy.authorize(task, adapter.metadata, invocation, now)
        result = adapter.invoke(invocation)
        validate_result(result, invocation, self.max_output_bytes)
        return result, make_audit_event(1, invocation, result, now)
