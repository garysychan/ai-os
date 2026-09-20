"""Explicit normalization adapters for existing runtime evidence."""

from __future__ import annotations

from ai_os.adapters import AdapterAuditEvent, AdapterStatus
from ai_os.controller import ControllerEventType, TraceEvent
from ai_os.execution import ExecutionEvent, ExecutionEventType
from ai_os.workflows import WorkflowEvent

from .errors import ObservabilityValidationError
from .models import RuntimeEvent, RuntimeEventSource, RuntimeEventType
from .validation import sanitize_event

_CONTROLLER_TYPES = {
    ControllerEventType.SESSION_STARTED: RuntimeEventType.ACCEPTED,
    ControllerEventType.AGENT_DISPATCHED: RuntimeEventType.STARTED,
    ControllerEventType.RESULT_RECORDED: RuntimeEventType.COMPLETED,
    ControllerEventType.TASK_TRANSITIONED: RuntimeEventType.ACCEPTED,
    ControllerEventType.SESSION_TERMINATED: RuntimeEventType.COMPLETED,
}
_EXECUTION_TYPES = {
    ExecutionEventType.SESSION_STARTED: RuntimeEventType.ACCEPTED,
    ExecutionEventType.STEP_STARTED: RuntimeEventType.STARTED,
    ExecutionEventType.STEP_FINISHED: RuntimeEventType.COMPLETED,
    ExecutionEventType.SESSION_FINISHED: RuntimeEventType.COMPLETED,
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


def from_controller(event: TraceEvent, *, trace_id: str | None = None) -> RuntimeEvent:
    return sanitize_event(
        RuntimeEvent(
            event_id=f"controller:{event.session_id}:{event.sequence}",
            sequence=event.sequence,
            timestamp=event.timestamp,
            event_type=_CONTROLLER_TYPES[event.event_type],
            source=RuntimeEventSource.CONTROLLER,
            task_id=event.task_id,
            trace_id=trace_id or event.session_id,
            session_id=event.session_id,
            agent_role=event.actor.value,
            summary=event.reason,
            correlation=event.correlation,
            evidence=event.evidence,
        )
    )


def from_execution(event: ExecutionEvent, *, trace_id: str | None = None) -> RuntimeEvent:
    return sanitize_event(
        RuntimeEvent(
            event_id=f"execution:{event.execution_id}:{event.sequence}",
            sequence=event.sequence,
            timestamp=event.timestamp,
            event_type=_EXECUTION_TYPES[event.event_type],
            source=RuntimeEventSource.EXECUTION,
            task_id=event.task_id,
            trace_id=trace_id or event.execution_id,
            execution_id=event.execution_id,
            summary=event.reason,
            correlation=tuple(
                (key, value)
                for key, value in (("step_id", event.step_id), ("attempt", _attempt(event)))
                if value is not None
            ),
            evidence=event.evidence,
        )
    )


def from_adapter(event: AdapterAuditEvent, *, trace_id: str | None = None) -> RuntimeEvent:
    return sanitize_event(
        RuntimeEvent(
            event_id=f"adapter:{event.invocation_id}:{event.sequence}",
            sequence=event.sequence,
            timestamp=event.timestamp,
            event_type=_ADAPTER_TYPES[event.status],
            source=RuntimeEventSource.ADAPTER,
            task_id=event.task_id,
            trace_id=trace_id or event.invocation_id,
            invocation_id=event.invocation_id,
            summary=f"{event.adapter}.{event.operation}: {event.status.value}",
            evidence=event.evidence,
        )
    )


def from_workflow(event: WorkflowEvent, *, trace_id: str | None = None) -> RuntimeEvent:
    try:
        event_type = _WORKFLOW_TYPES[event.event_type]
    except KeyError as error:
        raise ObservabilityValidationError(
            f"unsupported Workflow event type: {event.event_type}"
        ) from error
    return sanitize_event(
        RuntimeEvent(
            event_id=f"workflow:{event.session_id}:{event.sequence}",
            sequence=event.sequence,
            timestamp=event.timestamp,
            event_type=event_type,
            source=RuntimeEventSource.WORKFLOW,
            task_id=event.task_id,
            trace_id=trace_id or event.session_id,
            workflow_session_id=event.session_id,
            summary=event.summary,
            correlation=(("stage", event.stage),),
            evidence=event.evidence,
        )
    )


def _attempt(event: ExecutionEvent) -> str | None:
    return str(event.attempt) if event.attempt is not None else None
