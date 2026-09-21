from __future__ import annotations

import os
import signal
from datetime import UTC, datetime, timedelta
from threading import Event

import pytest

from ai_os.agents import AgentRole, Permission
from ai_os.monitoring import (
    HealthDetail,
    HealthStatus,
    MetricName,
    MetricPoint,
    MetricUnit,
    MonitoringAuthorizationError,
    MonitoringQueryContext,
    MonitoringService,
    MonitoringValidationError,
    RuntimeComponent,
    controller_health_sink,
    persistence_health_sink,
    validate_metric,
)
from ai_os.observability import RuntimeEvent, RuntimeEventSource, RuntimeEventType
from ai_os.persistence import SQLiteRuntimeStore, StoreConfig


NOW = datetime(2026, 9, 21, 12, tzinfo=UTC)


class Repository:
    def __init__(self, events: tuple[RuntimeEvent, ...] = ()) -> None:
        self.events = events

    def list_runtime_events(self, **_: object) -> tuple[RuntimeEvent, ...]:
        return self.events


class FailingProbe:
    component = RuntimeComponent.ADAPTER

    def check(self) -> HealthStatus:
        raise RuntimeError("private provider failure")


class InvalidProbe:
    component = RuntimeComponent.TOOL

    def check(self) -> str:
        return "/home/alice/private"


class SlowProbe:
    component = RuntimeComponent.CONTROLLER

    def check(self) -> HealthStatus:
        Event().wait(0.1)
        return HealthStatus.HEALTHY


class StubbornProbe:
    component = RuntimeComponent.EXECUTION

    def check(self) -> HealthStatus:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        Event().wait(10)
        return HealthStatus.HEALTHY


def event(event_type: RuntimeEventType, *, age: timedelta = timedelta()) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=f"event-{event_type.value.lower()}",
        sequence=1,
        timestamp=NOW - age,
        event_type=event_type,
        source=RuntimeEventSource.EXECUTION,
        task_id="TASK-0018",
        trace_id="trace-1",
        summary="[REDACTED]",
    )


def context(role: AgentRole = AgentRole.REVIEWER) -> MonitoringQueryContext:
    return MonitoringQueryContext(role, Permission.READ_CONTROL)


def test_metrics_are_bounded_aggregates() -> None:
    service = MonitoringService(
        Repository((event(RuntimeEventType.COMPLETED), event(RuntimeEventType.FAILED)))
    )

    points = service.metrics(context=context(), now=NOW)

    assert {point.name: point.value for point in points} == {
        "runtime.events.total": 2.0,
        "runtime.events.failed": 1.0,
        "runtime.events.denied": 0.0,
        "runtime.failure.rate": 0.5,
        "runtime.duration.average": 0.0,
        "runtime.query.capacity": 0.002,
    }


def test_metrics_derive_duration_from_trace_lifecycle() -> None:
    started = event(RuntimeEventType.STARTED, age=timedelta(seconds=10))
    completed = event(RuntimeEventType.COMPLETED)
    service = MonitoringService(Repository((completed, started)))

    points = {point.name: point.value for point in service.metrics(context=context(), now=NOW)}

    assert points["runtime.duration.average"] == 10.0


def test_health_reports_stale_and_degraded() -> None:
    stale = MonitoringService(
        Repository((event(RuntimeEventType.COMPLETED, age=timedelta(hours=1)),))
    ).health(context=context(), now=NOW)
    degraded = MonitoringService(Repository((event(RuntimeEventType.FAILED),))).health(
        context=context(), now=NOW
    )

    assert stale.status is HealthStatus.STALE
    assert degraded.status is HealthStatus.FAILED


def test_component_signal_is_included_without_execution_side_effect() -> None:
    service = MonitoringService(Repository((event(RuntimeEventType.COMPLETED),)))
    service.signal_sink(RuntimeComponent.PERSISTENCE)(HealthStatus.DEGRADED)

    snapshot = service.health(context=context(), now=NOW)

    assert snapshot.status is HealthStatus.DEGRADED
    assert snapshot.checks[-1].component is RuntimeComponent.PERSISTENCE


def test_runtime_integration_sinks_publish_canonical_health() -> None:
    from ai_os.controller import ControllerOutcome

    service = MonitoringService(Repository((event(RuntimeEventType.COMPLETED),)))
    controller_health_sink(service)(object(), ControllerOutcome.FAILED)  # type: ignore[arg-type]
    persistence_health_sink(service)(True)

    snapshot = service.health(context=context(), now=NOW)

    statuses = {check.component: check.status for check in snapshot.checks}
    assert statuses[RuntimeComponent.CONTROLLER] is HealthStatus.FAILED
    assert statuses[RuntimeComponent.PERSISTENCE] is HealthStatus.HEALTHY


def test_canonical_models_are_versioned() -> None:
    service = MonitoringService(Repository())
    snapshot = service.health(context=context(), now=NOW)

    assert snapshot.schema_version == 1
    assert snapshot.checks[0].schema_version == 1
    assert service.metrics(context=context(), now=NOW)[0].schema_version == 1


def test_probe_failure_is_isolated_as_unavailable() -> None:
    service = MonitoringService(
        Repository((event(RuntimeEventType.COMPLETED),)), probes=(FailingProbe(),)
    )

    snapshot = service.health(context=context(), now=NOW)

    assert snapshot.status is HealthStatus.UNAVAILABLE
    assert snapshot.checks[-1].summary is HealthDetail.PROBE_FAILED
    assert "private" not in repr(snapshot)


def test_invalid_probe_result_fails_closed() -> None:
    service = MonitoringService(Repository(), probes=(InvalidProbe(),))

    snapshot = service.health(context=context(), now=NOW)

    assert snapshot.checks[-1].status is HealthStatus.UNAVAILABLE
    assert snapshot.checks[-1].summary is HealthDetail.PROBE_FAILED


def test_probe_timeout_is_isolated() -> None:
    service = MonitoringService(
        Repository(), probes=(SlowProbe(),), probe_timeout_seconds=0.01
    )

    snapshot = service.health(context=context(), now=NOW)

    assert snapshot.status is HealthStatus.UNAVAILABLE
    assert snapshot.checks[-1].summary is HealthDetail.PROBE_TIMED_OUT


@pytest.mark.skipif(os.name != "posix", reason="SIGTERM behavior is POSIX-specific")
def test_probe_ignoring_sigterm_is_force_killed() -> None:
    service = MonitoringService(
        Repository(), probes=(StubbornProbe(),), probe_timeout_seconds=0.01
    )

    snapshot = service.health(context=context(), now=NOW)

    assert snapshot.status is HealthStatus.UNAVAILABLE
    assert snapshot.checks[-1].summary is HealthDetail.PROBE_TIMED_OUT


def test_query_authorization_fails_closed() -> None:
    service = MonitoringService(Repository())
    unauthorized = MonitoringQueryContext(AgentRole.DEVELOPER, Permission.MODIFY_CODE)

    with pytest.raises(MonitoringAuthorizationError):
        service.health(context=unauthorized, now=NOW)


def test_private_or_unbounded_metric_labels_are_rejected() -> None:
    point = MetricPoint(
        MetricName.EVENTS_TOTAL,
        1.0,
        MetricUnit.EVENTS,
        NOW,
        (("path", "/home/alice/private"),),
    )

    with pytest.raises(MonitoringValidationError, match="allowlisted"):
        validate_metric(point)


def test_unknown_metric_name_and_private_canonical_looking_value_fail_closed() -> None:
    with pytest.raises(MonitoringValidationError, match="canonical"):
        point = MetricPoint(  # type: ignore[arg-type]
            "private.metric", 1.0, MetricUnit.EVENTS, NOW
        )
        validate_metric(point)
    with pytest.raises(MonitoringValidationError, match="allowlisted"):
        validate_metric(
            MetricPoint(
                MetricName.EVENTS_TOTAL,
                1.0,
                MetricUnit.EVENTS,
                NOW,
                (("source", "CONFIDENTIAL_CUSTOMER_RECORD"),),
            )
        )


@pytest.mark.parametrize(
    ("name", "unit", "value"),
    [
        (MetricName.FAILURE_RATE, MetricUnit.EVENTS, 0.5),
        (MetricName.DURATION_AVERAGE, MetricUnit.RATIO, 0.5),
        (MetricName.EVENTS_TOTAL, MetricUnit.EVENTS, -10.0),
        (MetricName.FAILURE_RATE, MetricUnit.RATIO, 1.1),
    ],
)
def test_metric_semantics_fail_closed(
    name: MetricName, unit: MetricUnit, value: float
) -> None:
    with pytest.raises(MonitoringValidationError):
        validate_metric(MetricPoint(name, value, unit, NOW))


def test_invalid_health_models_fail_during_construction() -> None:
    from ai_os.monitoring import HealthCheck, HealthSnapshot

    with pytest.raises(MonitoringValidationError, match="schema version"):
        HealthCheck(
            RuntimeComponent.CONTROLLER,
            HealthStatus.HEALTHY,
            NOW,
            HealthDetail.NO_EVIDENCE,
            schema_version=99,
        )
    with pytest.raises(MonitoringValidationError, match="canonical"):
        HealthCheck(  # type: ignore[arg-type]
            RuntimeComponent.CONTROLLER, "PRIVATE", NOW, HealthDetail.NO_EVIDENCE
        )
    with pytest.raises(MonitoringValidationError, match="requires canonical checks"):
        HealthSnapshot(HealthStatus.HEALTHY, NOW, ())


def test_future_events_are_excluded_from_metric_window() -> None:
    future = event(RuntimeEventType.FAILED, age=timedelta(days=-1))

    points = {
        point.name: point.value
        for point in MonitoringService(Repository((future,))).metrics(context=context(), now=NOW)
    }

    assert points[MetricName.EVENTS_TOTAL] == 0.0
    assert points[MetricName.FAILURE_RATE] == 0.0


def test_monitoring_recovers_from_reopened_authoritative_store(tmp_path) -> None:
    database = tmp_path / "runtime.db"
    store = SQLiteRuntimeStore(StoreConfig(database=database))
    store.initialize()
    store.append_runtime_event(event(RuntimeEventType.COMPLETED))

    reopened = SQLiteRuntimeStore(StoreConfig(database=database))
    points = {
        point.name: point.value
        for point in MonitoringService(reopened).metrics(context=context(), now=NOW)
    }

    assert points[MetricName.EVENTS_TOTAL] == 1.0


@pytest.mark.parametrize("seconds", [0, -1, 604801])
def test_metric_windows_are_bounded(seconds: int) -> None:
    with pytest.raises(MonitoringValidationError):
        MonitoringService(Repository()).metrics(
            context=context(), window=timedelta(seconds=seconds), now=NOW
        )
