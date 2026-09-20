"""Governed service for appending and inspecting runtime evidence."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from ai_os.adapters import AdapterAuditEvent
from ai_os.controller import ControllerOutcome, TraceEvent
from ai_os.execution import (
    ExecutionEvent,
    ExecutionEventType,
    ExecutionOutcome,
    StepStatus,
)
from ai_os.tools import ToolInvocation, ToolResult
from ai_os.workflows import WorkflowEvent, WorkflowStatus

from .integrations import from_adapter, from_controller, from_execution, from_tool, from_workflow
from .models import RuntimeEvent, RuntimeEventFilter
from .validation import sanitize_event


class RuntimeEventRepository(Protocol):
    def append_runtime_event(self, event: RuntimeEvent) -> RuntimeEvent: ...

    def get_runtime_event(self, event_id: str) -> RuntimeEvent: ...

    def list_runtime_events(
        self, *, filters: RuntimeEventFilter | None = None, limit: int = 100
    ) -> tuple[RuntimeEvent, ...]: ...


class ObservabilityService:
    """Narrow evidence boundary; it never authorizes or executes runtime work."""

    def __init__(self, repository: RuntimeEventRepository) -> None:
        self.repository = repository

    def record(self, event: RuntimeEvent) -> RuntimeEvent:
        sanitized = sanitize_event(event, allow_unsequenced=True)
        return self.repository.append_runtime_event(sanitized)

    def get(self, event_id: str) -> RuntimeEvent:
        return self.repository.get_runtime_event(event_id)

    def list(
        self, *, filters: RuntimeEventFilter | None = None, limit: int = 100
    ) -> tuple[RuntimeEvent, ...]:
        return self.repository.list_runtime_events(filters=filters, limit=limit)

    def trace(self, trace_id: str, *, limit: int = 100) -> tuple[RuntimeEvent, ...]:
        return self.list(filters=RuntimeEventFilter(trace_id=trace_id), limit=limit)

    def adapter_sink(self, trace_id: str) -> Callable[[AdapterAuditEvent], None]:
        """Return a dependency-injected Adapter evidence sink."""

        def emit(event: AdapterAuditEvent) -> None:
            self.record(from_adapter(event, trace_id=trace_id))

        return emit

    def tool_sink(self, trace_id: str) -> Callable[[ToolInvocation, ToolResult], None]:
        """Return a dependency-injected Tool evidence sink."""

        def emit(invocation: ToolInvocation, result: ToolResult) -> None:
            self.record(from_tool(invocation, result, trace_id=trace_id))

        return emit

    def controller_sink(
        self, trace_id: str
    ) -> Callable[[TraceEvent, ControllerOutcome | None], None]:
        def emit(event: TraceEvent, outcome: ControllerOutcome | None) -> None:
            self.record(from_controller(event, trace_id=trace_id, outcome=outcome))

        return emit

    def execution_sink(self, trace_id: str) -> Callable[[ExecutionEvent, str | None, bool], None]:
        def emit(event: ExecutionEvent, status: str | None, timed_out: bool) -> None:
            outcome = None
            step_status = None
            if event.event_type is ExecutionEventType.SESSION_FINISHED and status is not None:
                outcome = ExecutionOutcome(status)
            if event.event_type is ExecutionEventType.STEP_FINISHED and status is not None:
                step_status = StepStatus(status)
            self.record(
                from_execution(
                    event,
                    trace_id=trace_id,
                    outcome=outcome,
                    step_status=step_status,
                    timed_out=timed_out,
                )
            )

        return emit

    def workflow_sink(
        self, trace_id: str
    ) -> Callable[[WorkflowEvent, WorkflowStatus | None, bool], None]:
        def emit(event: WorkflowEvent, status: WorkflowStatus | None, timed_out: bool) -> None:
            self.record(from_workflow(event, trace_id=trace_id, status=status, timed_out=timed_out))

        return emit
