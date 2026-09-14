"""Executable, provider-neutral Agent Runtime."""

from .base import Agent
from .errors import (
    AgentNotFoundError,
    AgentRuntimeError,
    AgentValidationError,
    AmbiguousRouteError,
    DuplicateAgentError,
    ExecutionPreconditionError,
    PermissionDeniedError,
    RoutingError,
)
from .models import (
    AgentDescriptor,
    AgentRole,
    Capability,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    Handoff,
    Permission,
)
from .permissions import PermissionPolicy
from .registry import AgentRegistry
from .roles import CanonicalAgent, canonical_agents
from .router import AgentRouter
from .runtime import AgentRuntime

__all__ = [
    "Agent", "AgentDescriptor", "AgentNotFoundError", "AgentRegistry",
    "AgentRole", "AgentRouter", "AgentRuntime", "AgentRuntimeError",
    "AgentValidationError", "AmbiguousRouteError", "CanonicalAgent",
    "Capability", "DuplicateAgentError", "ExecutionPreconditionError",
    "ExecutionRequest", "ExecutionResult", "ExecutionStatus", "Handoff",
    "Permission", "PermissionDeniedError", "PermissionPolicy",
    "RoutingError", "canonical_agents",
]
