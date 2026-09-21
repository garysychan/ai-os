"""Scheduler evidence integration with the canonical append-only audit store."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from ai_os.observability import RuntimeEvent, RuntimeEventSource, RuntimeEventType
from ai_os.persistence import SQLiteRuntimeStore

from .models import JobRecord

_EVENT_TYPES = {
    "SCHEDULED": RuntimeEventType.ACCEPTED,
    "STARTED": RuntimeEventType.STARTED,
    "SUCCEEDED": RuntimeEventType.COMPLETED,
    "FAILED": RuntimeEventType.FAILED,
    "RETRY_WAIT": RuntimeEventType.FAILED,
    "RELEASED": RuntimeEventType.CANCELLED,
    "CANCELLED": RuntimeEventType.CANCELLED,
    "TIMED_OUT": RuntimeEventType.TIMED_OUT,
}


def scheduler_runtime_event_sink(
    store: SQLiteRuntimeStore,
) -> Callable[[str, JobRecord], None]:
    """Return a failure-isolated sink accepted by SchedulerService."""

    def emit(event: str, record: JobRecord) -> None:
        store.append_runtime_event(
            RuntimeEvent(
                event_id=f"scheduler-{uuid4().hex}",
                sequence=0,
                timestamp=record.updated_at,
                event_type=_EVENT_TYPES[event],
                source=RuntimeEventSource.SCHEDULER,
                task_id=record.spec.task_id,
                trace_id=f"scheduler/{record.spec.job_id}",
                summary=event,
                correlation=(("attempt", str(max(record.attempts, 1))),),
            )
        )

    return emit
