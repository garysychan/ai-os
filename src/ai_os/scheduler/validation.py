"""Fail-closed Scheduler validation and authority checks."""

from __future__ import annotations

import re
from datetime import timedelta

from ai_os.agents import Permission, PermissionPolicy

from .errors import SchedulerAuthorizationError, SchedulerValidationError
from .models import JobSpec, ScheduleKind, SchedulerContext

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_TASK_ID = re.compile(r"^TASK-[0-9]{4}$")


def authorize(context: SchedulerContext, permission: Permission) -> None:
    if context.permission is not permission:
        raise SchedulerAuthorizationError(f"scheduler operation requires {permission.value}")
    if not PermissionPolicy().allows(context.actor_role, permission):
        raise SchedulerAuthorizationError("actor is not authorized for scheduler operation")


def validate_spec(spec: JobSpec) -> JobSpec:
    if spec.schema_version != 1:
        raise SchedulerValidationError("unsupported job schema version")
    if not _ID.fullmatch(spec.job_id) or not _TASK_ID.fullmatch(spec.task_id):
        raise SchedulerValidationError("job and task identifiers must be canonical")
    if not _ID.fullmatch(spec.workflow_name) or not _ID.fullmatch(spec.workflow_version):
        raise SchedulerValidationError("workflow identity must be canonical")
    if spec.run_at.tzinfo is None or spec.run_at.utcoffset() is None:
        raise SchedulerValidationError("run_at must be timezone-aware")
    if not isinstance(spec.kind, ScheduleKind):
        raise SchedulerValidationError("schedule kind must be canonical")
    if spec.kind is ScheduleKind.ONCE and spec.interval_seconds is not None:
        raise SchedulerValidationError("one-time jobs cannot define an interval")
    if spec.kind is ScheduleKind.INTERVAL and (
        spec.interval_seconds is None or not 60 <= spec.interval_seconds <= 2_592_000
    ):
        raise SchedulerValidationError("interval must be between one minute and thirty days")
    if not 1 <= spec.max_attempts <= 10:
        raise SchedulerValidationError("max_attempts must be within 1..10")
    if not 1 <= spec.retry_backoff_seconds <= 86_400:
        raise SchedulerValidationError("retry backoff must be within one day")
    if not 1 <= spec.timeout_seconds <= 86_400:
        raise SchedulerValidationError("timeout must be within one day")
    if timedelta(seconds=spec.retry_backoff_seconds * 2 ** (spec.max_attempts - 1)) > timedelta(
        days=7
    ):
        raise SchedulerValidationError("retry policy exceeds seven days")
    return spec
