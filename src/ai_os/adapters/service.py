"""Governed Adapter execution facade."""

from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime

from ai_os.tasks import Task

from .audit import make_audit_event
from .errors import AdapterError
from .models import AdapterAuditEvent, AdapterInvocation, AdapterResult, AdapterStatus
from .policy import AdapterPolicy
from .registry import AdapterRegistry
from .validation import validate_result


class AdapterService:
    def __init__(
        self,
        registry: AdapterRegistry,
        policy: AdapterPolicy | None = None,
        max_output_bytes: int = 1_100_000,
        audit_sink: Callable[[AdapterAuditEvent], None] | None = None,
    ) -> None:
        self.registry = registry
        self.policy = policy or AdapterPolicy()
        self.max_output_bytes = max_output_bytes
        self.audit_sink = audit_sink

    def execute(
        self,
        task: Task,
        invocation: AdapterInvocation,
        *,
        clock: Callable[[], datetime] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> tuple[AdapterResult, AdapterAuditEvent]:
        now = (clock or (lambda: datetime.now(UTC)))()
        try:
            adapter = self.registry.resolve(
                invocation.adapter, invocation.version, invocation.operation
            )
            self.policy.authorize(task, adapter.metadata, invocation, now)
        except AdapterError as error:
            denied = make_audit_event(
                1,
                invocation,
                AdapterResult(
                    invocation.invocation_id,
                    AdapterStatus.BLOCKED,
                    "Adapter invocation denied by policy",
                    evidence=(type(error).__name__,),
                ),
                now,
            )
            self._emit(denied)
            raise
        if cancelled is not None and cancelled():
            result = AdapterResult(
                invocation_id=invocation.invocation_id,
                status=AdapterStatus.CANCELLED,
                summary="Adapter invocation cancelled before execution",
                evidence=("cancelled=true",),
            )
            audit = make_audit_event(1, invocation, result, now)
            self._emit(audit)
            return result, audit
        result = adapter.invoke(invocation)
        validate_result(result, invocation, self.max_output_bytes)
        audit = make_audit_event(1, invocation, result, now)
        self._emit(audit)
        return result, audit

    def _emit(self, event: AdapterAuditEvent) -> None:
        if self.audit_sink is not None:
            with suppress(Exception):
                self.audit_sink(event)
