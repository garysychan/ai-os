"""Transactional SQLite Scheduler repository."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from datetime import datetime, timedelta
from uuid import uuid4

from ai_os.persistence import SQLiteRuntimeStore, StoreConfig

from .codec import dump_job, load_job
from .errors import SchedulerConflictError, SchedulerNotFoundError
from .models import TERMINAL_JOB_STATES, JobRecord, JobSpec, JobState
from .state_machine import require_transition


class SQLiteSchedulerStore:
    """Persist and atomically lease bounded Scheduler jobs."""

    def __init__(self, config: StoreConfig) -> None:
        self.config = config
        self.runtime_store = SQLiteRuntimeStore(config)
        self.database = self.runtime_store.database

    def initialize(self) -> None:
        self.runtime_store.initialize()

    def create(self, spec: JobSpec, *, now: datetime) -> JobRecord:
        record = JobRecord(spec, JobState.SCHEDULED, 0, spec.run_at, now, now)
        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO scheduler_jobs(
                       job_id, task_id, workflow_name, workflow_version, state, next_run_at,
                       lease_owner, lease_token, lease_expires_at, updated_at, payload
                       ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?)""",
                    (
                        spec.job_id,
                        spec.task_id,
                        spec.workflow_name,
                        spec.workflow_version,
                        record.state.value,
                        record.next_run_at.isoformat(),
                        now.isoformat(),
                        dump_job(record),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise SchedulerConflictError(f"duplicate job: {spec.job_id}") from error
        return record

    def get(self, job_id: str) -> JobRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM scheduler_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        if row is None:
            raise SchedulerNotFoundError(f"unknown job: {job_id}")
        return load_job(str(row[0]))

    def list(self, *, limit: int = 100) -> tuple[JobRecord, ...]:
        bounded = self._bounded(limit)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM scheduler_jobs ORDER BY created_at, job_id LIMIT ?".replace(
                    "created_at", "updated_at"
                ),
                (bounded,),
            ).fetchall()
        return tuple(load_job(str(row[0])) for row in rows)

    def claim_due(self, *, worker_id: str, now: datetime, lease_seconds: int) -> JobRecord | None:
        expires = now + timedelta(seconds=lease_seconds)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT payload FROM scheduler_jobs
                   WHERE state IN (?, ?, ?, ?) AND next_run_at <= ?
                     AND (lease_expires_at IS NULL OR lease_expires_at <= ?)
                   ORDER BY next_run_at, job_id LIMIT 1""",
                (
                    JobState.SCHEDULED.value,
                    JobState.RETRY_WAIT.value,
                    JobState.LEASED.value,
                    JobState.RUNNING.value,
                    now.isoformat(),
                    now.isoformat(),
                ),
            ).fetchone()
            if row is None:
                connection.rollback()
                return None
            current = load_job(str(row[0]))
            token = uuid4().hex
            claimed = replace(
                current,
                state=JobState.LEASED,
                lease_owner=worker_id,
                lease_token=token,
                lease_expires_at=expires,
                updated_at=now,
            )
            require_transition(current.state, claimed.state)
            updated = connection.execute(
                """UPDATE scheduler_jobs SET state=?, lease_owner=?, lease_token=?,
                   lease_expires_at=?, updated_at=?, payload=?
                   WHERE job_id=? AND state IN (?, ?, ?, ?)""",
                (
                    claimed.state.value,
                    worker_id,
                    token,
                    expires.isoformat(),
                    now.isoformat(),
                    dump_job(claimed),
                    current.spec.job_id,
                    JobState.SCHEDULED.value,
                    JobState.RETRY_WAIT.value,
                    JobState.LEASED.value,
                    JobState.RUNNING.value,
                ),
            ).rowcount
            if updated != 1:
                connection.rollback()
                raise SchedulerConflictError("job claim lost to a concurrent worker")
            connection.commit()
            return claimed

    def renew(
        self, job_id: str, *, lease_token: str, now: datetime, lease_seconds: int
    ) -> JobRecord:
        current = self.get(job_id)
        if (
            current.state not in {JobState.LEASED, JobState.RUNNING}
            or current.lease_token != lease_token
            or current.lease_expires_at is None
            or current.lease_expires_at <= now
        ):
            raise SchedulerConflictError("only the current unexpired lease can be renewed")
        renewed = replace(
            current,
            lease_expires_at=now + timedelta(seconds=lease_seconds),
            updated_at=now,
        )
        return self.save_leased(renewed, lease_token=lease_token)

    def save_leased(self, record: JobRecord, *, lease_token: str) -> JobRecord:
        with self._connect() as connection:
            updated = connection.execute(
                """UPDATE scheduler_jobs SET state=?, next_run_at=?, lease_owner=?,
                   lease_token=?, lease_expires_at=?, updated_at=?, payload=?
                   WHERE job_id=? AND lease_token=?""",
                (
                    record.state.value,
                    record.next_run_at.isoformat(),
                    record.lease_owner,
                    record.lease_token,
                    record.lease_expires_at.isoformat() if record.lease_expires_at else None,
                    record.updated_at.isoformat(),
                    dump_job(record),
                    record.spec.job_id,
                    lease_token,
                ),
            ).rowcount
        if updated != 1:
            raise SchedulerConflictError("stale or invalid lease token")
        return record

    def cancel(self, job_id: str, *, now: datetime) -> JobRecord:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload FROM scheduler_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            if row is None:
                connection.rollback()
                raise SchedulerNotFoundError(f"unknown job: {job_id}")
            current = load_job(str(row[0]))
            if current.state in TERMINAL_JOB_STATES:
                connection.rollback()
                raise SchedulerConflictError("terminal job cannot be cancelled")
            require_transition(current.state, JobState.CANCELLED)
            cancelled = replace(
                current,
                state=JobState.CANCELLED,
                updated_at=now,
                lease_owner=None,
                lease_token=None,
                lease_expires_at=None,
            )
            updated = connection.execute(
                """UPDATE scheduler_jobs SET state=?, lease_owner=NULL, lease_token=NULL,
                   lease_expires_at=NULL, updated_at=?, payload=?
                   WHERE job_id=? AND state=?""",
                (
                    JobState.CANCELLED.value,
                    now.isoformat(),
                    dump_job(cancelled),
                    job_id,
                    current.state.value,
                ),
            ).rowcount
            if updated != 1:
                connection.rollback()
                raise SchedulerConflictError("job changed while cancellation was requested")
            connection.commit()
        return cancelled

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database,
            timeout=self.config.busy_timeout_ms / 1000,
            isolation_level="DEFERRED",
        )
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _bounded(self, limit: int) -> int:
        if isinstance(limit, bool) or not 1 <= limit <= self.config.max_query_limit:
            raise SchedulerConflictError("query limit is outside configured bounds")
        return limit
