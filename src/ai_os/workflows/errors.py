"""Errors raised by the governed Workflow Engine."""


class WorkflowError(Exception):
    """Base Workflow Engine error."""


class WorkflowRegistryError(WorkflowError):
    """Raised when Workflow registration or resolution fails closed."""


class WorkflowValidationError(WorkflowError):
    """Raised when a Workflow model or checkpoint is invalid."""


class WorkflowPolicyError(WorkflowError):
    """Raised when Workflow execution is not authorized."""
