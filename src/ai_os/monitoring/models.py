"""Immutable runtime metrics and health models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from ai_os.agents import AgentRole, Permission

from .errors import MonitoringValidationError


class HealthStatus(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"
    STALE = "STALE"


class RuntimeComponent(StrEnum):
    CONTROLLER = "CONTROLLER"
    EXECUTION = "EXECUTION"
    ADAPTER = "ADAPTER"
    TOOL = "TOOL"
    WORKFLOW = "WORKFLOW"
    PERSISTENCE = "PERSISTENCE"
    OBSERVABILITY = "OBSERVABILITY"
    SCHEDULER = "SCHEDULER"


class MetricName(StrEnum):
    EVENTS_TOTAL = "runtime.events.total"
    EVENTS_FAILED = "runtime.events.failed"
    EVENTS_DENIED = "runtime.events.denied"
    FAILURE_RATE = "runtime.failure.rate"
    DURATION_AVERAGE = "runtime.duration.average"
    QUERY_CAPACITY = "runtime.query.capacity"


class MetricUnit(StrEnum):
    EVENTS = "events"
    RATIO = "ratio"
    SECONDS = "seconds"


class HealthDetail(StrEnum):
    NO_EVIDENCE = "NO_EVIDENCE"
    AUDIT_DERIVED = "AUDIT_DERIVED"
    EXPLICIT_SIGNAL = "EXPLICIT_SIGNAL"
    PROBE_COMPLETED = "PROBE_COMPLETED"
    PROBE_TIMED_OUT = "PROBE_TIMED_OUT"
    PROBE_FAILED = "PROBE_FAILED"


@dataclass(frozen=True)
class MonitoringQueryContext:
    actor_role: AgentRole
    permission: Permission


@dataclass(frozen=True)
class MetricPoint:
    name: MetricName
    value: float
    unit: MetricUnit
    timestamp: datetime
    labels: tuple[tuple[str, str], ...] = ()
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise MonitoringValidationError("unsupported metric schema version")


@dataclass(frozen=True)
class HealthCheck:
    component: RuntimeComponent
    status: HealthStatus
    checked_at: datetime
    summary: HealthDetail
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise MonitoringValidationError("unsupported health-check schema version")
        if not isinstance(self.component, RuntimeComponent):
            raise MonitoringValidationError("health component must be canonical")
        if not isinstance(self.status, HealthStatus) or not isinstance(self.summary, HealthDetail):
            raise MonitoringValidationError("health status and detail must be canonical")
        if self.checked_at.tzinfo is None or self.checked_at.utcoffset() is None:
            raise MonitoringValidationError("health-check timestamp must be timezone-aware")


@dataclass(frozen=True)
class HealthSnapshot:
    status: HealthStatus
    checked_at: datetime
    checks: tuple[HealthCheck, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise MonitoringValidationError("unsupported health snapshot schema version")
        if not isinstance(self.status, HealthStatus):
            raise MonitoringValidationError("health snapshot status must be canonical")
        if self.checked_at.tzinfo is None or self.checked_at.utcoffset() is None:
            raise MonitoringValidationError("health snapshot timestamp must be timezone-aware")
        if not self.checks or any(not isinstance(check, HealthCheck) for check in self.checks):
            raise MonitoringValidationError("health snapshot requires canonical checks")


class HealthProbe(Protocol):
    component: RuntimeComponent

    def check(self) -> HealthStatus: ...
