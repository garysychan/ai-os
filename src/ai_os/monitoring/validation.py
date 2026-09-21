"""Fail-closed validation and authorization for runtime monitoring."""

from __future__ import annotations

import math

from ai_os.agents import Permission, PermissionPolicy

from .errors import MonitoringAuthorizationError, MonitoringValidationError
from ai_os.observability import RuntimeEventSource, RuntimeEventType

from .models import HealthStatus, MetricName, MetricPoint, MetricUnit, MonitoringQueryContext

_SAFE_LABELS = frozenset({"source", "event_type", "status"})
_LABEL_VALUES = {
    "source": frozenset(item.value for item in RuntimeEventSource),
    "event_type": frozenset(item.value for item in RuntimeEventType),
    "status": frozenset(item.value for item in HealthStatus),
}
_METRIC_UNITS = {
    MetricName.EVENTS_TOTAL: MetricUnit.EVENTS,
    MetricName.EVENTS_FAILED: MetricUnit.EVENTS,
    MetricName.EVENTS_DENIED: MetricUnit.EVENTS,
    MetricName.FAILURE_RATE: MetricUnit.RATIO,
    MetricName.DURATION_AVERAGE: MetricUnit.SECONDS,
    MetricName.QUERY_CAPACITY: MetricUnit.RATIO,
}


def authorize_monitoring_query(context: MonitoringQueryContext) -> None:
    if context.permission is not Permission.READ_CONTROL:
        raise MonitoringAuthorizationError("monitoring query requires read_control")
    if not PermissionPolicy().allows(context.actor_role, Permission.READ_CONTROL):
        raise MonitoringAuthorizationError("actor is not authorized to inspect monitoring data")


def validate_metric(point: MetricPoint) -> MetricPoint:
    if point.schema_version != 1:
        raise MonitoringValidationError("unsupported metric schema version")
    if not isinstance(point.name, MetricName) or not isinstance(point.unit, MetricUnit):
        raise MonitoringValidationError("metric name and unit must be canonical")
    if _METRIC_UNITS[point.name] is not point.unit:
        raise MonitoringValidationError("metric unit does not match its canonical name")
    if point.timestamp.tzinfo is None or point.timestamp.utcoffset() is None:
        raise MonitoringValidationError("metric timestamp must be timezone-aware")
    if (
        not isinstance(point.value, (int, float))
        or isinstance(point.value, bool)
        or not math.isfinite(point.value)
    ):
        raise MonitoringValidationError("metric value must be finite and numeric")
    if point.value < 0:
        raise MonitoringValidationError("metric value must be non-negative")
    if point.unit is MetricUnit.RATIO and point.value > 1:
        raise MonitoringValidationError("metric ratio must be within zero and one")
    if len(point.labels) > 3 or len({key for key, _ in point.labels}) != len(point.labels):
        raise MonitoringValidationError("metric labels must be unique and bounded")
    for key, value in point.labels:
        if key not in _SAFE_LABELS or value not in _LABEL_VALUES[key]:
            raise MonitoringValidationError("metric label is not allowlisted")
    return point


def validate_metrics(points: tuple[MetricPoint, ...], *, max_series: int = 256) -> None:
    if len(points) > max_series:
        raise MonitoringValidationError("metric series cardinality exceeds the configured bound")
    series = {(point.name, point.labels) for point in points}
    if len(series) != len(points):
        raise MonitoringValidationError("duplicate metric series are not allowed")
    for point in points:
        validate_metric(point)
