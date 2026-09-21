"""Runtime Scheduler errors."""


class SchedulerError(Exception):
    """Base Scheduler failure."""


class SchedulerValidationError(SchedulerError):
    """Invalid schedule, job or transition."""


class SchedulerAuthorizationError(SchedulerError):
    """Caller lacks Scheduler authority."""


class SchedulerConflictError(SchedulerError):
    """Concurrent claim, lease or state conflict."""


class SchedulerNotFoundError(SchedulerError):
    """Requested job does not exist."""
