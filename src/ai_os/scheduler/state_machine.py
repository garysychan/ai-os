"""Explicit fail-closed Scheduler job state machine."""

from .errors import SchedulerConflictError
from .models import JobState

ALLOWED_JOB_TRANSITIONS = frozenset(
    {
        (JobState.SCHEDULED, JobState.LEASED),
        (JobState.SCHEDULED, JobState.CANCELLED),
        (JobState.RETRY_WAIT, JobState.LEASED),
        (JobState.RETRY_WAIT, JobState.CANCELLED),
        (JobState.LEASED, JobState.RUNNING),
        (JobState.LEASED, JobState.LEASED),
        (JobState.LEASED, JobState.CANCELLED),
        (JobState.RUNNING, JobState.LEASED),
        (JobState.RUNNING, JobState.SUCCEEDED),
        (JobState.RUNNING, JobState.SCHEDULED),
        (JobState.RUNNING, JobState.RETRY_WAIT),
        (JobState.RUNNING, JobState.FAILED),
        (JobState.RUNNING, JobState.TIMED_OUT),
        (JobState.RUNNING, JobState.CANCELLED),
    }
)


def require_transition(source: JobState, target: JobState) -> None:
    if (source, target) not in ALLOWED_JOB_TRANSITIONS:
        raise SchedulerConflictError(f"illegal scheduler transition: {source}->{target}")
