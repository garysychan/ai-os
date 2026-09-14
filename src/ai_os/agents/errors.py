"""Typed Agent Runtime errors."""


class AgentRuntimeError(Exception):
    """Base error for all Agent Runtime failures."""


class AgentValidationError(AgentRuntimeError):
    """An Agent definition or request is invalid."""


class DuplicateAgentError(AgentRuntimeError):
    """A role is already registered."""


class AgentNotFoundError(AgentRuntimeError):
    """No Agent is registered for a requested role."""


class RoutingError(AgentRuntimeError):
    """A request cannot be routed deterministically."""


class AmbiguousRouteError(RoutingError):
    """More than one Agent can satisfy a request."""


class PermissionDeniedError(AgentRuntimeError):
    """An Agent lacks an explicitly granted permission."""


class ExecutionPreconditionError(AgentRuntimeError):
    """Task state or dependency preconditions are not satisfied."""
