"""Governed Scheduler orchestration without direct execution authority."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from ai_os.agents import Permission

from .errors import SchedulerConflictError, SchedulerValidationError
from .models import (
    DispatchRequest,
    JobRecord,
    JobSpec,
    JobState,
    ScheduleKind,
    SchedulerContext,
)
from .store import SQLiteSchedulerStore
from .validation import authorize, validate_spec

EvidenceSink = Callable[[str, JobRecord], None]


class SchedulerService:
    def __init__(
        self,
        store: SQLiteSchedulerStore,
        *,
        approved_tasks: frozenset[str],
        registered_workflows: frozenset[tuple[str, str]],
        evidence_sink: EvidenceSink | None = None,
    ) -> None:
        self.store = store
        self.approved_tasks = approved_tasks
        self.registered_workflows = registered_workflows
        self.evidence_sink = evidence_sink

    def create(
        self, spec: JobSpec, *, context: SchedulerContext, now: datetime | None = None
    ) -> JobRecord:
        authorize(context, Permission.COORDINATE)
        validate_spec(spec)
        if spec.task_id not in self.approved_tasks:
            raise SchedulerValidationError("job task is not approved for scheduling")
        if (spec.workflow_name, spec.workflow_version) not in self.registered_workflows:
            raise SchedulerValidationError("job workflow is not registered")
        instant = now or datetime.now(UTC)
        if spec.run_at < instant - timedelta(seconds=1):
            raise SchedulerValidationError("job cannot be scheduled in the past")
        record = self.store.create(spec, now=instant)
        self._emit("SCHEDULED", record)
        return record

    def get(self, job_id: str, *, context: SchedulerContext) -> JobRecord:
        authorize(context, Permission.READ_CONTROL)
        return self.store.get(job_id)

    def list(self, *, context: SchedulerContext, limit: int = 100) -> tuple[JobRecord, ...]:
        authorize(context, Permission.READ_CONTROL)
        return self.store.list(limit=limit)

    def cancel(
        self, job_id: str, *, context: SchedulerContext, now: datetime | None = None
    ) -> JobRecord:
        authorize(context, Permission.COORDINATE)
        record = self.store.cancel(job_id, now=now or datetime.now(UTC))
        self._emit("CANCELLED", record)
        return record

    def claim(
        self,
        *,
        worker_id: str,
        context: SchedulerContext,
        now: datetime | None = None,
        lease_seconds: int = 60,
    ) -> DispatchRequest | None:
        authorize(context, Permission.COORDINATE)
        if not worker_id or len(worker_id) > 64 or not 5 <= lease_seconds <= 300:
            raise SchedulerValidationError("worker identity or lease duration is invalid")
        instant = now or datetime.now(UTC)
        record = self.store.claim_due(worker_id=worker_id, now=instant, lease_seconds=lease_seconds)
        if record is None:
            return None
        if (
            record.spec.task_id not in self.approved_tasks
            or (
                record.spec.workflow_name,
                record.spec.workflow_version,
            )
            not in self.registered_workflows
        ):
            raise SchedulerValidationError("leased job no longer passes dispatch policy")
        assert record.lease_token is not None
        running = replace(
            record,
            state=JobState.RUNNING,
            attempts=record.attempts + 1,
            updated_at=instant,
        )
        self.store.save_leased(running, lease_token=record.lease_token)
        self._emit("STARTED", running)
        return DispatchRequest(
            job_id=running.spec.job_id,
            task_id=running.spec.task_id,
            workflow_name=running.spec.workflow_name,
            workflow_version=running.spec.workflow_version,
            attempt=running.attempts,
            lease_token=record.lease_token,
            deadline=instant + timedelta(seconds=running.spec.timeout_seconds),
        )

    def complete(
        self,
        request: DispatchRequest,
        *,
        succeeded: bool,
        now: datetime | None = None,
    ) -> JobRecord:
        instant = now or datetime.now(UTC)
        current = self.store.get(request.job_id)
        if current.state is not JobState.RUNNING or current.lease_token != request.lease_token:
            raise SchedulerConflictError("completion requires the current running lease")
        if instant > request.deadline:
            state = JobState.TIMED_OUT
            next_run = current.next_run_at
            error = "TIMEOUT"
        elif succeeded and current.spec.kind is ScheduleKind.INTERVAL:
            state = JobState.SCHEDULED
            assert current.spec.interval_seconds is not None
            next_run = instant + timedelta(seconds=current.spec.interval_seconds)
            error = None
        elif succeeded:
            state = JobState.SUCCEEDED
            next_run = current.next_run_at
            error = None
        elif current.attempts < current.spec.max_attempts:
            state = JobState.RETRY_WAIT
            backoff = current.spec.retry_backoff_seconds * 2 ** (current.attempts - 1)
            next_run = instant + timedelta(seconds=backoff)
            error = "FAILED"
        else:
            state = JobState.FAILED
            next_run = current.next_run_at
            error = "FAILED"
        updated = replace(
            current,
            state=state,
            next_run_at=next_run,
            updated_at=instant,
            lease_owner=None,
            lease_token=None,
            lease_expires_at=None,
            last_error=error,
        )
        self.store.save_leased(updated, lease_token=request.lease_token)
        self._emit(state.value, updated)
        return updated

    def _emit(self, event: str, record: JobRecord) -> None:
        if self.evidence_sink is not None:
            with suppress(Exception):
                self.evidence_sink(event, record)
