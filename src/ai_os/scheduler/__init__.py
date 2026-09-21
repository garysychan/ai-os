"""Governed Runtime Scheduler public API."""

from .errors import (
    SchedulerAuthorizationError,
    SchedulerConflictError,
    SchedulerError,
    SchedulerNotFoundError,
    SchedulerValidationError,
)
from .gateway import DispatchPolicySnapshot, WorkflowDispatchGateway
from .integrations import scheduler_runtime_event_sink
from .models import (
    TERMINAL_JOB_STATES,
    DispatchRequest,
    JobAttempt,
    JobLease,
    JobRecord,
    JobResult,
    JobSpec,
    JobState,
    ScheduleKind,
    SchedulerContext,
    WorkerLimits,
)
from .service import SchedulerService
from .state_machine import ALLOWED_JOB_TRANSITIONS, require_transition
from .store import SQLiteSchedulerStore
from .validation import validate_spec
from .worker import SchedulerWorker

__all__ = [
    "DispatchRequest",
    "DispatchPolicySnapshot",
    "WorkflowDispatchGateway",
    "JobAttempt",
    "JobLease",
    "JobRecord",
    "JobResult",
    "JobSpec",
    "JobState",
    "SQLiteSchedulerStore",
    "ScheduleKind",
    "SchedulerAuthorizationError",
    "SchedulerConflictError",
    "SchedulerContext",
    "SchedulerError",
    "SchedulerNotFoundError",
    "SchedulerService",
    "SchedulerValidationError",
    "SchedulerWorker",
    "TERMINAL_JOB_STATES",
    "WorkerLimits",
    "ALLOWED_JOB_TRANSITIONS",
    "require_transition",
    "validate_spec",
    "scheduler_runtime_event_sink",
]
