"""Explicit normalization adapters for existing runtime evidence."""

from __future__ import annotations

from ai_os.adapters import AdapterAuditEvent, AdapterStatus
from ai_os.controller import ControllerEventType, ControllerOutcome, TraceEvent
from ai_os.execution import (
    ExecutionEvent,
    ExecutionEventType,
    ExecutionOutcome,
    StepStatus,
)
from ai_os.tools import ToolInvocation, ToolResult
from ai_os.workflows import WorkflowEvent, WorkflowStatus

from .errors import ObservabilityValidationError
from .models import RuntimeEvent, RuntimeEventSource, RuntimeEventType
from .validation import sanitize_event

_CONTROLLER_TYPES = {
    ControllerEventType.SESSION_STARTED: RuntimeEventType.ACCEPTED,
    ControllerEventType.AGENT_DISPATCHED: RuntimeEventType.STARTED,
    ControllerEventType.RESULT_RECORDED: RuntimeEventType.COMPLETED,
    ControllerEventType.TASK_TRANSITIONED: RuntimeEventType.ACCEPTED,
}
_EXECUTION_TYPES = {
    ExecutionEventType.SESSION_STARTED: RuntimeEventType.ACCEPTED,
    ExecutionEventType.STEP_STARTED: RuntimeEventType.STARTED,
}
_ADAPTER_TYPES = {
    AdapterStatus.SUCCESS: RuntimeEventType.COMPLETED,
    AdapterStatus.BLOCKED: RuntimeEventType.DENIED,
    AdapterStatus.FAILED: RuntimeEventType.FAILED,
    AdapterStatus.CANCELLED: RuntimeEventType.CANCELLED,
}
_WORKFLOW_TYPES = {
    "WORKFLOW_STARTED": RuntimeEventType.ACCEPTED,
    "SESSION_STARTED": RuntimeEventType.ACCEPTED,
    "AGENT_DISPATCHED": RuntimeEventType.STARTED,
    "RESULT_RECORDED": RuntimeEventType.COMPLETED,
    "TASK_TRANSITIONED": RuntimeEventType.ACCEPTED,
    "SESSION_TERMINATED": RuntimeEventType.COMPLETED,
    "WORKFLOW_ABORTED": RuntimeEventType.FAILED,
}


def from_controller(
    event: TraceEvent,
    *,
    trace_id: str | None = None,
    outcome: ControllerOutcome | None = None,
    timed_out: bool = False,
) -> RuntimeEvent:
    event_type = (
        _terminal_type(outcome.value if outcome else None, timed_out=timed_out)
        if event.event_type is ControllerEventType.SESSION_TERMINATED
        else _CONTROLLER_TYPES[event.event_type]
    )
    return sanitize_event(
        RuntimeEvent(
            event_id=f"controller:{event.session_id}:{event.sequence}",
            sequence=0,
            timestamp=event.timestamp,
            event_type=event_type,
            source=RuntimeEventSource.CONTROLLER,
            task_id=event.task_id,
            trace_id=trace_id or event.session_id,
            session_id=event.session_id,
            agent_role=event.actor.value,
            summary=event.reason,
            correlation=((*event.correlation, ("source_sequence", str(event.sequence)))),
            evidence=event.evidence,
        ),
        allow_unsequenced=True,
    )


def from_execution(
    event: ExecutionEvent,
    *,
    trace_id: str | None = None,
    outcome: ExecutionOutcome | None = None,
    step_status: StepStatus | None = None,
    timed_out: bool = False,
) -> RuntimeEvent:
    event_type = _EXECUTION_TYPES.get(event.event_type)
    if event.event_type is ExecutionEventType.STEP_FINISHED:
        event_type = _terminal_type(step_status.value if step_status else None, timed_out=timed_out)
    elif event.event_type is ExecutionEventType.SESSION_FINISHED:
        event_type = _terminal_type(outcome.value if outcome else None, timed_out=timed_out)
    if event_type is None:
        raise ObservabilityValidationError("unsupported Execution event type")
    return sanitize_event(
        RuntimeEvent(
            event_id=f"execution:{event.execution_id}:{event.sequence}",
            sequence=0,
            timestamp=event.timestamp,
            event_type=event_type,
            source=RuntimeEventSource.EXECUTION,
            task_id=event.task_id,
            trace_id=trace_id or event.execution_id,
            execution_id=event.execution_id,
            summary=event.reason,
            correlation=tuple(
                (key, value)
                for key, value in (
                    ("step_id", event.step_id),
                    ("attempt", _attempt(event)),
                    ("source_sequence", str(event.sequence)),
                )
                if value is not None
            ),
            evidence=event.evidence,
        ),
        allow_unsequenced=True,
    )


def from_adapter(event: AdapterAuditEvent, *, trace_id: str | None = None) -> RuntimeEvent:
    return sanitize_event(
        RuntimeEvent(
            event_id=f"adapter:{event.invocation_id}:{event.sequence}",
            sequence=0,
            timestamp=event.timestamp,
            event_type=_ADAPTER_TYPES[event.status],
            source=RuntimeEventSource.ADAPTER,
            task_id=event.task_id,
            trace_id=trace_id or event.invocation_id,
            invocation_id=event.invocation_id,
            summary=f"{event.adapter}.{event.operation}: {event.status.value}",
            correlation=(("source_sequence", str(event.sequence)),),
            evidence=event.evidence,
        ),
        allow_unsequenced=True,
    )


def from_workflow(
    event: WorkflowEvent,
    *,
    trace_id: str | None = None,
    status: WorkflowStatus | None = None,
    timed_out: bool = False,
) -> RuntimeEvent:
    try:
        event_type = _WORKFLOW_TYPES[event.event_type]
    except KeyError as error:
        raise ObservabilityValidationError(
            f"unsupported Workflow event type: {event.event_type}"
        ) from error
    if event.event_type in {"WORKFLOW_ABORTED", "SESSION_TERMINATED"}:
        event_type = _terminal_type(status.value if status else event.stage, timed_out=timed_out)
    return sanitize_event(
        RuntimeEvent(
            event_id=f"workflow:{event.session_id}:{event.sequence}",
            sequence=0,
            timestamp=event.timestamp,
            event_type=event_type,
            source=RuntimeEventSource.WORKFLOW,
            task_id=event.task_id,
            trace_id=trace_id or event.session_id,
            workflow_session_id=event.session_id,
            summary=event.summary,
            correlation=(("stage", event.stage), ("source_sequence", str(event.sequence))),
            evidence=event.evidence,
        ),
        allow_unsequenced=True,
    )


def _attempt(event: ExecutionEvent) -> str | None:
    return str(event.attempt) if event.attempt is not None else None


def from_tool(
    invocation: ToolInvocation, result: ToolResult, *, trace_id: str | None = None
) -> RuntimeEvent:
    return sanitize_event(
        RuntimeEvent(
            event_id=f"tool:{invocation.invocation_id}:1",
            sequence=0,
            timestamp=result.audit.timestamp,
            event_type=_ADAPTER_TYPES[result.adapter_result.status],
            source=RuntimeEventSource.TOOL,
            task_id=invocation.task_id,
            trace_id=trace_id or invocation.invocation_id,
            invocation_id=invocation.invocation_id,
            agent_role=invocation.agent_role.value,
            summary=(
                f"{invocation.tool}.{invocation.operation}: {result.adapter_result.status.value}"
            ),
            correlation=(("source_sequence", "1"),),
            evidence=(*invocation.approval_evidence, *result.adapter_result.evidence),
        ),
        allow_unsequenced=True,
    )


def _terminal_type(status: str | None, *, timed_out: bool) -> RuntimeEventType:
    if timed_out:
        return RuntimeEventType.TIMED_OUT
    mapping = {
        "COMPLETED": RuntimeEventType.COMPLETED,
        "SUCCESS": RuntimeEventType.COMPLETED,
        "BLOCKED": RuntimeEventType.DENIED,
        "FAILED": RuntimeEventType.FAILED,
        "ESCALATED": RuntimeEventType.FAILED,
        "CANCELLED": RuntimeEventType.CANCELLED,
    }
    try:
        return mapping[status or ""]
    except KeyError as error:
        raise ObservabilityValidationError("terminal runtime outcome is required") from error
