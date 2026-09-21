"""Read-only runtime metrics and health service."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from multiprocessing import get_context
from queue import Empty
from typing import Protocol

from ai_os.observability import RuntimeEvent, RuntimeEventFilter, RuntimeEventType

from .errors import MonitoringValidationError
from .models import (
    HealthCheck,
    HealthDetail,
    HealthProbe,
    HealthSnapshot,
    HealthStatus,
    MetricName,
    MetricPoint,
    MetricUnit,
    MonitoringQueryContext,
    RuntimeComponent,
)
from .validation import authorize_monitoring_query, validate_metrics


class MonitoringEventRepository(Protocol):
    """Minimal read-only event contract required by monitoring."""

    def list_runtime_events(
        self, *, filters: RuntimeEventFilter | None = None, limit: int = 100
    ) -> tuple[RuntimeEvent, ...]: ...


class ProbeResultQueue(Protocol):
    """Narrow queue contract used by an isolated health probe worker."""

    def put(self, item: tuple[str, str | None]) -> None: ...


class MonitoringService:
    """Derive bounded monitoring views without mutating runtime state."""

    def __init__(
        self,
        repository: MonitoringEventRepository,
        *,
        max_limit: int = 1000,
        probes: tuple[HealthProbe, ...] = (),
        probe_timeout_seconds: float = 1.0,
    ) -> None:
        if max_limit < 1 or max_limit > 10_000:
            raise MonitoringValidationError("monitoring capacity must be within 1..10000")
        if probe_timeout_seconds <= 0 or probe_timeout_seconds > 5:
            raise MonitoringValidationError("probe timeout must be within five seconds")
        self.repository = repository
        self.max_limit = max_limit
        self.probes = probes
        self.probe_timeout_seconds = probe_timeout_seconds
        self._signals: dict[RuntimeComponent, HealthStatus] = {}

    def signal_sink(self, component: RuntimeComponent) -> Callable[[HealthStatus], None]:
        """Return a narrow signal sink with no execution authority."""

        if not isinstance(component, RuntimeComponent):
            raise MonitoringValidationError("health signal component is invalid")

        def emit(status: HealthStatus) -> None:
            if not isinstance(status, HealthStatus):
                raise MonitoringValidationError("health signal status is invalid")
            self._signals[component] = status

        return emit

    def metrics(
        self,
        *,
        context: MonitoringQueryContext,
        window: timedelta = timedelta(hours=1),
        now: datetime | None = None,
    ) -> tuple[MetricPoint, ...]:
        authorize_monitoring_query(context)
        instant = now or datetime.now(UTC)
        if window <= timedelta(0) or window > timedelta(days=7):
            raise MonitoringValidationError("metric window must be within seven days")
        events = self._events()
        recent = tuple(event for event in events if instant - window <= event.timestamp <= instant)
        counts = Counter(event.event_type.value for event in recent)
        terminal = {
            RuntimeEventType.COMPLETED,
            RuntimeEventType.FAILED,
            RuntimeEventType.CANCELLED,
            RuntimeEventType.TIMED_OUT,
        }
        traces: dict[str, list[RuntimeEvent]] = {}
        for event in recent:
            traces.setdefault(event.trace_id, []).append(event)
        durations = []
        for trace in traces.values():
            started = [
                event.timestamp for event in trace if event.event_type is RuntimeEventType.STARTED
            ]
            ended = [event.timestamp for event in trace if event.event_type in terminal]
            if started and ended and max(ended) >= min(started):
                durations.append((max(ended) - min(started)).total_seconds())
        failures = counts[RuntimeEventType.FAILED.value] + counts[RuntimeEventType.TIMED_OUT.value]
        terminals = sum(counts[item.value] for item in terminal)
        points = [
            MetricPoint(MetricName.EVENTS_TOTAL, float(len(recent)), MetricUnit.EVENTS, instant),
            MetricPoint(
                MetricName.EVENTS_FAILED,
                float(counts[RuntimeEventType.FAILED.value]),
                MetricUnit.EVENTS,
                instant,
            ),
            MetricPoint(
                MetricName.EVENTS_DENIED,
                float(counts[RuntimeEventType.DENIED.value]),
                MetricUnit.EVENTS,
                instant,
            ),
            MetricPoint(
                MetricName.FAILURE_RATE,
                failures / terminals if terminals else 0.0,
                MetricUnit.RATIO,
                instant,
            ),
            MetricPoint(
                MetricName.DURATION_AVERAGE,
                sum(durations) / len(durations) if durations else 0.0,
                MetricUnit.SECONDS,
                instant,
            ),
            MetricPoint(
                MetricName.QUERY_CAPACITY,
                min(len(events) / self.max_limit, 1.0),
                MetricUnit.RATIO,
                instant,
            ),
        ]
        result = tuple(points)
        validate_metrics(result)
        return result

    def health(
        self,
        *,
        context: MonitoringQueryContext,
        stale_after: timedelta = timedelta(minutes=15),
        now: datetime | None = None,
    ) -> HealthSnapshot:
        authorize_monitoring_query(context)
        instant = now or datetime.now(UTC)
        if stale_after <= timedelta(0) or stale_after > timedelta(days=1):
            raise MonitoringValidationError("stale threshold must be within one day")
        events = self._events()
        if not events:
            check = HealthCheck(
                RuntimeComponent.OBSERVABILITY,
                HealthStatus.UNAVAILABLE,
                instant,
                HealthDetail.NO_EVIDENCE,
            )
        else:
            latest = max(events, key=lambda event: event.timestamp)
            if latest.timestamp < instant - stale_after:
                status = HealthStatus.STALE
            elif latest.event_type is RuntimeEventType.FAILED:
                status = HealthStatus.FAILED
            elif latest.event_type is RuntimeEventType.TIMED_OUT:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY
            check = HealthCheck(
                RuntimeComponent.OBSERVABILITY,
                status,
                instant,
                HealthDetail.AUDIT_DERIVED,
            )
        checks = [check]
        checks.extend(
            HealthCheck(component, status, instant, HealthDetail.EXPLICIT_SIGNAL)
            for component, status in sorted(self._signals.items(), key=lambda item: item[0].value)
        )
        checks.extend(self._run_probes(instant, timeout_seconds=self.probe_timeout_seconds))
        overall = max((item.status for item in checks), key=_health_severity)
        return HealthSnapshot(overall, instant, tuple(checks))

    def _run_probes(self, instant: datetime, *, timeout_seconds: float) -> tuple[HealthCheck, ...]:
        checks: list[HealthCheck] = []
        for probe in self.probes:
            component = getattr(probe, "component", None)
            if not isinstance(component, RuntimeComponent):
                raise MonitoringValidationError("probe component is invalid")
            context = get_context("spawn")
            queue = context.Queue(maxsize=1)
            process = context.Process(target=_probe_worker, args=(probe, queue), daemon=True)
            try:
                process.start()
                process.join(timeout_seconds)
                if process.is_alive():
                    process.terminate()
                    process.join(0.1)
                    if process.is_alive():
                        process.kill()
                        process.join(0.1)
                    status = HealthStatus.UNAVAILABLE
                    summary = HealthDetail.PROBE_TIMED_OUT
                else:
                    kind, value = queue.get_nowait()
                    if kind == "error":
                        status = HealthStatus.UNAVAILABLE
                        summary = HealthDetail.PROBE_FAILED
                    else:
                        status = HealthStatus(value)
                        summary = HealthDetail.PROBE_COMPLETED
            except (Empty, ValueError, TypeError):
                status = HealthStatus.UNAVAILABLE
                summary = HealthDetail.PROBE_FAILED
            except Exception:
                status = HealthStatus.UNAVAILABLE
                summary = HealthDetail.PROBE_FAILED
            finally:
                if process.is_alive():
                    process.kill()
                    process.join(0.1)
                queue.close()
                queue.cancel_join_thread()
                process.close()
            checks.append(HealthCheck(component, status, instant, summary))
        return tuple(checks)

    def _events(self) -> tuple[RuntimeEvent, ...]:
        return self.repository.list_runtime_events(
            filters=RuntimeEventFilter(), limit=self.max_limit
        )


def _health_severity(status: HealthStatus) -> int:
    return {
        HealthStatus.HEALTHY: 0,
        HealthStatus.STALE: 1,
        HealthStatus.DEGRADED: 2,
        HealthStatus.UNAVAILABLE: 3,
        HealthStatus.FAILED: 4,
    }[status]


def _probe_worker(probe: HealthProbe, queue: ProbeResultQueue) -> None:
    try:
        status = probe.check()
        queue.put(("status", status.value if isinstance(status, HealthStatus) else "INVALID"))
    except Exception:
        queue.put(("error", None))
