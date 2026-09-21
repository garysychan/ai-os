"""Dependency-injected health signal adapters for installed runtime boundaries."""

from __future__ import annotations

from collections.abc import Callable

from ai_os.adapters import AdapterAuditEvent, AdapterStatus
from ai_os.controller import ControllerOutcome, TraceEvent
from ai_os.execution import ExecutionEvent
from ai_os.tools import ToolInvocation, ToolResult
from ai_os.workflows import WorkflowEvent, WorkflowStatus

from .models import HealthStatus, RuntimeComponent
from .service import MonitoringService


def controller_health_sink(
    service: MonitoringService,
) -> Callable[[TraceEvent, ControllerOutcome | None], None]:
    signal = service.signal_sink(RuntimeComponent.CONTROLLER)

    def emit(_: TraceEvent, outcome: ControllerOutcome | None) -> None:
        signal(_outcome_health(outcome.value if outcome else None))

    return emit


def execution_health_sink(
    service: MonitoringService,
) -> Callable[[ExecutionEvent, str | None, bool], None]:
    signal = service.signal_sink(RuntimeComponent.EXECUTION)

    def emit(_: ExecutionEvent, status: str | None, timed_out: bool) -> None:
        signal(HealthStatus.DEGRADED if timed_out else _outcome_health(status))

    return emit


def adapter_health_sink(service: MonitoringService) -> Callable[[AdapterAuditEvent], None]:
    signal = service.signal_sink(RuntimeComponent.ADAPTER)

    def emit(event: AdapterAuditEvent) -> None:
        mapping = {
            AdapterStatus.SUCCESS: HealthStatus.HEALTHY,
            AdapterStatus.BLOCKED: HealthStatus.DEGRADED,
            AdapterStatus.CANCELLED: HealthStatus.DEGRADED,
            AdapterStatus.FAILED: HealthStatus.FAILED,
        }
        signal(mapping[event.status])

    return emit


def tool_health_sink(
    service: MonitoringService,
) -> Callable[[ToolInvocation, ToolResult], None]:
    signal = service.signal_sink(RuntimeComponent.TOOL)

    def emit(_: ToolInvocation, result: ToolResult) -> None:
        status = result.adapter_result.status
        signal(HealthStatus.HEALTHY if status is AdapterStatus.SUCCESS else HealthStatus.DEGRADED)

    return emit


def workflow_health_sink(
    service: MonitoringService,
) -> Callable[[WorkflowEvent, WorkflowStatus | None, bool], None]:
    signal = service.signal_sink(RuntimeComponent.WORKFLOW)

    def emit(_: WorkflowEvent, status: WorkflowStatus | None, timed_out: bool) -> None:
        value = status.value if status else None
        signal(HealthStatus.DEGRADED if timed_out else _outcome_health(value))

    return emit


def persistence_health_sink(service: MonitoringService) -> Callable[[bool], None]:
    signal = service.signal_sink(RuntimeComponent.PERSISTENCE)
    return lambda available: signal(HealthStatus.HEALTHY if available else HealthStatus.UNAVAILABLE)


def observability_health_sink(service: MonitoringService) -> Callable[[bool], None]:
    signal = service.signal_sink(RuntimeComponent.OBSERVABILITY)
    return lambda available: signal(HealthStatus.HEALTHY if available else HealthStatus.UNAVAILABLE)


def _outcome_health(status: str | None) -> HealthStatus:
    if status in {None, "COMPLETED", "SUCCESS"}:
        return HealthStatus.HEALTHY
    if status == "FAILED":
        return HealthStatus.FAILED
    return HealthStatus.DEGRADED
