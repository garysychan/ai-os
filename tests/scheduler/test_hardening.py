from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Lock
from time import sleep
from types import SimpleNamespace

import pytest

from ai_os.agents import AgentRole, Permission
from ai_os.persistence import StoreConfig
from ai_os.scheduler import (
    DispatchPolicySnapshot,
    DispatchRequest,
    JobSpec,
    JobState,
    SchedulerConflictError,
    SchedulerContext,
    SchedulerService,
    SchedulerValidationError,
    SchedulerWorker,
    SQLiteSchedulerStore,
    WorkerLimits,
    WorkflowDispatchGateway,
    require_transition,
)
from ai_os.tasks import AcceptanceCriterion, Priority, Task, TaskStatus
from ai_os.workflows import WorkflowStatus

NOW = datetime(2026, 9, 21, 12, tzinfo=UTC)
CONTEXT = SchedulerContext(AgentRole.CONTROLLER, Permission.COORDINATE)


def build(tmp_path: Path) -> SchedulerService:
    store = SQLiteSchedulerStore(StoreConfig(database=tmp_path / "runtime.db"))
    store.initialize()
    return SchedulerService(
        store,
        approved_tasks=frozenset({"TASK-0019"}),
        registered_workflows=frozenset({("coding", "1")}),
    )


def job(job_id: str = "job-hardening", **changes: object) -> JobSpec:
    return replace(JobSpec(job_id, "TASK-0019", "coding", "1", NOW), **changes)


def test_illegal_transition_fails_closed() -> None:
    with pytest.raises(SchedulerConflictError):
        require_transition(JobState.SCHEDULED, JobState.SUCCEEDED)


def test_lease_renewal_requires_current_unexpired_fencing_token(tmp_path: Path) -> None:
    scheduler = build(tmp_path)
    scheduler.create(job(), context=CONTEXT, now=NOW)
    request = scheduler.claim(worker_id="worker-a", context=CONTEXT, now=NOW, lease_seconds=10)
    assert request is not None

    renewed = scheduler.renew(
        request, context=CONTEXT, now=NOW + timedelta(seconds=5), lease_seconds=20
    )
    assert renewed.lease_expires_at == NOW + timedelta(seconds=25)
    with pytest.raises(SchedulerConflictError):
        scheduler.renew(
            replace(request, lease_token="stale"),
            context=CONTEXT,
            now=NOW + timedelta(seconds=6),
        )


def test_retry_uses_deterministic_jitter_and_elapsed_budget(tmp_path: Path) -> None:
    scheduler = build(tmp_path)
    scheduler.create(
        job(max_attempts=3, retry_backoff_seconds=10, jitter_seconds=5),
        context=CONTEXT,
        now=NOW,
    )
    request = scheduler.claim(worker_id="worker-a", context=CONTEXT, now=NOW)
    assert request is not None
    first = scheduler.complete(request, succeeded=False, now=NOW)
    assert NOW + timedelta(seconds=10) <= first.next_run_at <= NOW + timedelta(seconds=15)

    scheduler.create(
        job(
            "job-budget",
            timeout_seconds=1,
            max_attempts=2,
            retry_backoff_seconds=10,
            max_elapsed_seconds=5,
        ),
        context=CONTEXT,
        now=NOW,
    )
    budget = scheduler.claim(worker_id="worker-a", context=CONTEXT, now=NOW)
    assert budget is not None
    exhausted = scheduler.complete(budget, succeeded=False, now=NOW)
    assert exhausted.state is JobState.FAILED
    assert exhausted.last_error == "ELAPSED_BUDGET_EXHAUSTED"


def test_concurrent_claim_has_one_winner(tmp_path: Path) -> None:
    scheduler = build(tmp_path)
    scheduler.create(job(), context=CONTEXT, now=NOW)

    def claim(worker: str):
        return scheduler.claim(worker_id=worker, context=CONTEXT, now=NOW)

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = tuple(executor.map(claim, (f"worker-{index}" for index in range(8))))
    assert sum(result is not None for result in results) == 1


class RecordingGateway:
    def __init__(self, *, succeed: bool = True) -> None:
        self.succeed = succeed
        self.jobs: list[str] = []
        self.lock = Lock()

    def dispatch(self, request, *, clock, cancelled) -> bool:
        assert not cancelled()
        with self.lock:
            self.jobs.append(request.job_id)
        return self.succeed


def test_worker_enforces_batch_and_concurrency_limits(tmp_path: Path) -> None:
    scheduler = build(tmp_path)
    for index in range(4):
        scheduler.create(job(f"job-{index}"), context=CONTEXT, now=NOW)
    gateway = RecordingGateway()
    worker = SchedulerWorker(
        scheduler,
        gateway,
        worker_id="worker-batch",
        limits=WorkerLimits(max_concurrency=2, max_batch=3, poll_seconds=0.1),
    )

    assert worker.run_batch(clock=lambda: NOW) == 3
    assert len(gateway.jobs) == 3
    assert sum(item.state is JobState.SUCCEEDED for item in scheduler.store.list()) == 3


def test_worker_renews_lease_during_long_dispatch(tmp_path: Path, monkeypatch) -> None:
    scheduler = build(tmp_path)
    scheduler.create(job(), context=CONTEXT, now=NOW)
    renewals: list[str] = []
    original = scheduler.renew

    def record_renewal(request, **kwargs):
        renewals.append(request.job_id)
        return original(request, **kwargs)

    monkeypatch.setattr(scheduler, "renew", record_renewal)

    class SlowGateway(RecordingGateway):
        def dispatch(self, request, *, clock, cancelled) -> bool:
            sleep(0.25)
            assert not cancelled()
            return super().dispatch(request, clock=clock, cancelled=cancelled)

    worker = SchedulerWorker(
        scheduler,
        SlowGateway(),
        worker_id="worker-renew",
        limits=WorkerLimits(lease_seconds=5, renewal_seconds=0.1),
    )

    assert worker.run_batch(clock=lambda: NOW) == 1
    assert renewals
    assert scheduler.store.get("job-hardening").state is JobState.SUCCEEDED


def test_lease_loss_requests_cooperative_cancellation(tmp_path: Path, monkeypatch) -> None:
    scheduler = build(tmp_path)
    scheduler.create(job(), context=CONTEXT, now=NOW)
    cancellation_seen = Event()

    def lose_lease(*args, **kwargs):
        raise SchedulerConflictError("lease lost")

    monkeypatch.setattr(scheduler, "renew", lose_lease)

    class CancellationGateway(RecordingGateway):
        def dispatch(self, request, *, clock, cancelled) -> bool:
            for _ in range(50):
                if cancelled():
                    cancellation_seen.set()
                    return False
                sleep(0.01)
            return True

    worker = SchedulerWorker(
        scheduler,
        CancellationGateway(),
        worker_id="worker-lease-loss",
        limits=WorkerLimits(lease_seconds=5, renewal_seconds=0.1),
    )

    assert worker.run_batch(clock=lambda: NOW) == 1
    assert cancellation_seen.is_set()
    assert scheduler.store.get("job-hardening").state is JobState.RUNNING


def test_worker_queue_capacity_bounds_claimed_work(tmp_path: Path) -> None:
    scheduler = build(tmp_path)
    for index in range(5):
        scheduler.create(job(f"job-queue-{index}"), context=CONTEXT, now=NOW)
    worker = SchedulerWorker(
        scheduler,
        RecordingGateway(),
        worker_id="worker-queue",
        limits=WorkerLimits(max_concurrency=2, max_queue=0, max_batch=5),
    )

    assert worker.run_batch(clock=lambda: NOW) == 2
    assert sum(item.state is JobState.SUCCEEDED for item in scheduler.store.list()) == 2


def test_worker_cooperative_shutdown_does_not_claim(tmp_path: Path) -> None:
    scheduler = build(tmp_path)
    scheduler.create(job(), context=CONTEXT, now=NOW)
    stopped = Event()
    stopped.set()
    worker = SchedulerWorker(
        scheduler, RecordingGateway(), worker_id="worker-stop", stop_event=stopped
    )

    assert worker.run_batch(clock=lambda: NOW) == 0
    assert scheduler.store.get("job-hardening").state is JobState.SCHEDULED


def test_mid_batch_shutdown_releases_claimed_work(tmp_path: Path, monkeypatch) -> None:
    scheduler = build(tmp_path)
    scheduler.create(job(), context=CONTEXT, now=NOW)
    stopped = Event()
    original = scheduler.claim

    def claim_then_stop(**kwargs):
        request = original(**kwargs)
        stopped.set()
        return request

    monkeypatch.setattr(scheduler, "claim", claim_then_stop)
    worker = SchedulerWorker(
        scheduler,
        RecordingGateway(),
        worker_id="worker-mid-stop",
        stop_event=stopped,
    )

    assert worker.run_batch(clock=lambda: NOW) == 0
    released = scheduler.store.get("job-hardening")
    assert released.state is JobState.SCHEDULED
    assert released.lease_token is None
    assert released.last_error == "COOPERATIVE_SHUTDOWN"


@pytest.mark.parametrize(
    "limits",
    [
        WorkerLimits(max_concurrency=0),
        WorkerLimits(max_queue=101),
        WorkerLimits(max_batch=101),
        WorkerLimits(poll_seconds=0),
        WorkerLimits(lease_seconds=4),
        WorkerLimits(renewal_seconds=60),
    ],
)
def test_invalid_worker_limits_fail_closed(tmp_path: Path, limits: WorkerLimits) -> None:
    with pytest.raises(SchedulerValidationError):
        SchedulerWorker(build(tmp_path), RecordingGateway(), worker_id="worker", limits=limits)


def test_cancel_and_complete_race_preserves_one_terminal_outcome(tmp_path: Path) -> None:
    scheduler = build(tmp_path)
    scheduler.create(job(), context=CONTEXT, now=NOW)
    request = scheduler.claim(worker_id="worker-race", context=CONTEXT, now=NOW)
    assert request is not None

    def cancel():
        try:
            return scheduler.cancel("job-hardening", context=CONTEXT, now=NOW)
        except SchedulerConflictError:
            return None

    def complete():
        try:
            return scheduler.complete(request, succeeded=True, now=NOW)
        except SchedulerConflictError:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = tuple(executor.map(lambda operation: operation(), (cancel, complete)))

    assert sum(outcome is not None for outcome in outcomes) == 1
    assert scheduler.store.get("job-hardening").state in {
        JobState.CANCELLED,
        JobState.SUCCEEDED,
    }


class WorkflowEngineStub:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run(self, task, workflow, version, objective, **kwargs):
        self.calls.append(
            {
                "task": task,
                "workflow": workflow,
                "version": version,
                "objective": objective,
                **kwargs,
            }
        )
        return SimpleNamespace(session=SimpleNamespace(status=WorkflowStatus.COMPLETED))


def runtime_task(status: TaskStatus = TaskStatus.IN_PROGRESS) -> Task:
    return Task(
        "TASK-0019",
        "Scheduler",
        Priority.P1,
        status,
        ("Controller",),
        (),
        (AcceptanceCriterion("approved", True, ("CR-2026-016",)),),
    )


def test_workflow_gateway_revalidates_and_uses_existing_authority_chain() -> None:
    engine = WorkflowEngineStub()
    snapshot = DispatchPolicySnapshot(
        runtime_task(), {}, "governed scheduled work", ("CR-2026-016 APPROVED",)
    )
    gateway = WorkflowDispatchGateway(engine, lambda _: snapshot)  # type: ignore[arg-type]
    request = DispatchRequest(
        "job-gateway",
        "TASK-0019",
        "coding",
        "1",
        1,
        "fence-token",
        NOW + timedelta(minutes=5),
    )

    assert gateway.dispatch(request, clock=lambda: NOW, cancelled=lambda: False)
    assert engine.calls[0]["task"] == snapshot.task
    assert engine.calls[0]["approval_evidence"] == snapshot.approval_evidence


def test_workflow_gateway_rejects_stale_task_policy() -> None:
    engine = WorkflowEngineStub()
    gateway = WorkflowDispatchGateway(  # type: ignore[arg-type]
        engine,
        lambda _: DispatchPolicySnapshot(runtime_task(TaskStatus.DONE), {}, "stale"),
    )
    request = DispatchRequest(
        "job-gateway",
        "TASK-0019",
        "coding",
        "1",
        1,
        "fence-token",
        NOW + timedelta(minutes=5),
    )

    with pytest.raises(SchedulerValidationError):
        gateway.dispatch(request, clock=lambda: NOW, cancelled=lambda: False)
