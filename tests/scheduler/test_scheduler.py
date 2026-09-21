from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ai_os.agents import AgentRole, Permission
from ai_os.observability import RuntimeEventSource
from ai_os.persistence import CURRENT_SCHEMA_VERSION, StoreConfig
from ai_os.scheduler import (
    JobSpec,
    JobState,
    ScheduleKind,
    SchedulerAuthorizationError,
    SchedulerConflictError,
    SchedulerContext,
    SchedulerService,
    SchedulerValidationError,
    SQLiteSchedulerStore,
    scheduler_runtime_event_sink,
)

NOW = datetime(2026, 9, 21, 12, tzinfo=UTC)


def controller() -> SchedulerContext:
    return SchedulerContext(AgentRole.CONTROLLER, Permission.COORDINATE)


def reader() -> SchedulerContext:
    return SchedulerContext(AgentRole.REVIEWER, Permission.READ_CONTROL)


def spec(**changes: object) -> JobSpec:
    base = JobSpec("job-1", "TASK-0019", "coding", "1", NOW)
    return replace(base, **changes)


def service(path: Path) -> SchedulerService:
    store = SQLiteSchedulerStore(StoreConfig(database=path))
    store.initialize()
    assert store.runtime_store.status().schema_version == CURRENT_SCHEMA_VERSION
    return SchedulerService(
        store,
        approved_tasks=frozenset({"TASK-0019"}),
        registered_workflows=frozenset({("coding", "1")}),
    )


def test_create_persist_reopen_and_list(tmp_path: Path) -> None:
    first = service(tmp_path / "runtime.db")
    created = first.create(spec(), context=controller(), now=NOW)
    reopened = service(tmp_path / "runtime.db")

    assert created.state is JobState.SCHEDULED
    assert reopened.get("job-1", context=reader()) == created
    assert reopened.list(context=reader()) == (created,)


def test_authority_and_registration_fail_closed(tmp_path: Path) -> None:
    scheduler = service(tmp_path / "runtime.db")
    with pytest.raises(SchedulerAuthorizationError):
        scheduler.create(spec(), context=reader(), now=NOW)
    with pytest.raises(SchedulerValidationError):
        scheduler.create(spec(task_id="TASK-9999"), context=controller(), now=NOW)
    with pytest.raises(SchedulerValidationError):
        scheduler.create(spec(workflow_name="unknown"), context=controller(), now=NOW)


def test_atomic_claim_and_fenced_completion(tmp_path: Path) -> None:
    scheduler = service(tmp_path / "runtime.db")
    scheduler.create(spec(), context=controller(), now=NOW)

    request = scheduler.claim(worker_id="worker-a", context=controller(), now=NOW)

    assert request is not None
    assert scheduler.claim(worker_id="worker-b", context=controller(), now=NOW) is None
    with pytest.raises(SchedulerConflictError):
        scheduler.complete(replace(request, lease_token="stale"), succeeded=True, now=NOW)
    completed = scheduler.complete(request, succeeded=True, now=NOW)
    assert completed.state is JobState.SUCCEEDED


def test_expired_lease_is_reclaimed_with_new_fencing_token(tmp_path: Path) -> None:
    scheduler = service(tmp_path / "runtime.db")
    scheduler.create(spec(), context=controller(), now=NOW)
    first = scheduler.claim(worker_id="worker-a", context=controller(), now=NOW, lease_seconds=5)
    second = scheduler.claim(
        worker_id="worker-b", context=controller(), now=NOW + timedelta(seconds=6)
    )

    assert first is not None and second is not None
    assert first.lease_token != second.lease_token
    with pytest.raises(SchedulerConflictError):
        scheduler.complete(first, succeeded=True, now=NOW + timedelta(seconds=7))


def test_failure_retries_with_bounded_exponential_backoff(tmp_path: Path) -> None:
    scheduler = service(tmp_path / "runtime.db")
    scheduler.create(spec(max_attempts=2, retry_backoff_seconds=10), context=controller(), now=NOW)
    first = scheduler.claim(worker_id="worker-a", context=controller(), now=NOW)
    assert first is not None
    retry = scheduler.complete(first, succeeded=False, now=NOW)
    assert retry.state is JobState.RETRY_WAIT
    assert retry.next_run_at == NOW + timedelta(seconds=10)
    second = scheduler.claim(worker_id="worker-a", context=controller(), now=retry.next_run_at)
    assert second is not None
    failed = scheduler.complete(second, succeeded=False, now=retry.next_run_at)
    assert failed.state is JobState.FAILED


def test_interval_job_schedules_from_completion_without_catch_up(tmp_path: Path) -> None:
    scheduler = service(tmp_path / "runtime.db")
    scheduler.create(
        spec(kind=ScheduleKind.INTERVAL, interval_seconds=60),
        context=controller(),
        now=NOW,
    )
    request = scheduler.claim(worker_id="worker-a", context=controller(), now=NOW)
    assert request is not None
    completed_at = NOW + timedelta(seconds=5)
    record = scheduler.complete(request, succeeded=True, now=completed_at)
    assert record.state is JobState.SCHEDULED
    assert record.next_run_at == completed_at + timedelta(seconds=60)


def test_cancel_and_timeout_are_terminal(tmp_path: Path) -> None:
    scheduler = service(tmp_path / "runtime.db")
    scheduler.create(spec(), context=controller(), now=NOW)
    cancelled = scheduler.cancel("job-1", context=controller(), now=NOW)
    assert cancelled.state is JobState.CANCELLED
    with pytest.raises(SchedulerConflictError):
        scheduler.cancel("job-1", context=controller(), now=NOW)

    scheduler.create(spec(job_id="job-2", timeout_seconds=1), context=controller(), now=NOW)
    request = scheduler.claim(worker_id="worker-a", context=controller(), now=NOW)
    assert request is not None
    timed_out = scheduler.complete(request, succeeded=True, now=NOW + timedelta(seconds=2))
    assert timed_out.state is JobState.TIMED_OUT


@pytest.mark.parametrize(
    "item",
    [
        spec(job_id="bad id"),
        spec(run_at=datetime(2026, 9, 21)),
        spec(kind=ScheduleKind.INTERVAL, interval_seconds=30),
        spec(max_attempts=11),
        spec(timeout_seconds=0),
    ],
)
def test_invalid_specs_fail_closed(tmp_path: Path, item: JobSpec) -> None:
    scheduler = service(tmp_path / f"{abs(hash(item))}.db")
    with pytest.raises(SchedulerValidationError):
        scheduler.create(item, context=controller(), now=NOW)


def test_scheduler_emits_canonical_redacted_runtime_events(tmp_path: Path) -> None:
    store = SQLiteSchedulerStore(StoreConfig(database=tmp_path / "runtime.db"))
    store.initialize()
    scheduler = SchedulerService(
        store,
        approved_tasks=frozenset({"TASK-0019"}),
        registered_workflows=frozenset({("coding", "1")}),
        evidence_sink=scheduler_runtime_event_sink(store.runtime_store),
    )

    scheduler.create(spec(), context=controller(), now=NOW)
    request = scheduler.claim(worker_id="worker-a", context=controller(), now=NOW)
    assert request is not None
    scheduler.complete(request, succeeded=True, now=NOW)

    events = store.runtime_store.list_runtime_events(limit=10)
    assert [event.source for event in events] == [RuntimeEventSource.SCHEDULER] * 3
    assert [event.summary for event in events] == ["[REDACTED]"] * 3
