from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Lock
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


@pytest.mark.parametrize(
    "limits",
    [
        WorkerLimits(max_concurrency=0),
        WorkerLimits(max_batch=101),
        WorkerLimits(poll_seconds=0),
    ],
)
def test_invalid_worker_limits_fail_closed(tmp_path: Path, limits: WorkerLimits) -> None:
    with pytest.raises(SchedulerValidationError):
        SchedulerWorker(build(tmp_path), RecordingGateway(), worker_id="worker", limits=limits)


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
