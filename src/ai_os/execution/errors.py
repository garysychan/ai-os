"""Execution Engine errors."""


class ExecutionEngineError(Exception):
    """Base error for governed execution."""


class ExecutionValidationError(ExecutionEngineError):
    """Raised when a plan, step, context, or session is invalid."""


class ExecutionPolicyError(ExecutionEngineError):
    """Raised when execution would violate an authority boundary."""


class AdapterRegistryError(ExecutionEngineError):
    """Raised when adapter registration or resolution is invalid."""
