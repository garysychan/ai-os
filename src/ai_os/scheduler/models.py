"""Immutable versioned Scheduler models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from ai_os.agents import AgentRole, Permission


class ScheduleKind(StrEnum):
    ONCE = "ONCE"
    INTERVAL = "INTERVAL"


class JobState(StrEnum):
    SCHEDULED = "SCHEDULED"
    LEASED = "LEASED"
    RUNNING = "RUNNING"
    RETRY_WAIT = "RETRY_WAIT"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


TERMINAL_JOB_STATES = frozenset(
    {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED, JobState.TIMED_OUT}
)


@dataclass(frozen=True)
class SchedulerContext:
    actor_role: AgentRole
    permission: Permission


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    task_id: str
    workflow_name: str
    workflow_version: str
    run_at: datetime
    kind: ScheduleKind = ScheduleKind.ONCE
    interval_seconds: int | None = None
    max_attempts: int = 1
    retry_backoff_seconds: int = 30
    timeout_seconds: int = 300
    schema_version: int = 1


@dataclass(frozen=True)
class JobRecord:
    spec: JobSpec
    state: JobState
    attempts: int
    next_run_at: datetime
    created_at: datetime
    updated_at: datetime
    lease_owner: str | None = None
    lease_token: str | None = None
    lease_expires_at: datetime | None = None
    last_error: str | None = None
    schema_version: int = 1


@dataclass(frozen=True)
class DispatchRequest:
    job_id: str
    task_id: str
    workflow_name: str
    workflow_version: str
    attempt: int
    lease_token: str
    deadline: datetime
    schema_version: int = 1
