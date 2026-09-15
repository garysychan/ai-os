"""Controller orchestration errors."""


class ControllerError(Exception):
    """Base error for Controller orchestration."""


class ControllerValidationError(ControllerError):
    """Raised when a session or orchestration request is invalid."""


class ControllerPolicyError(ControllerError):
    """Raised when an orchestration policy gate blocks execution."""
