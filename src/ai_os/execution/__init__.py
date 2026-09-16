"""Governed provider-neutral Execution Engine."""

from .context import append_event, create_session, finish_session, record_result
from .engine import ExecutionEngine
from .errors import (
    AdapterRegistryError,
    ExecutionEngineError,
    ExecutionPolicyError,
    ExecutionValidationError,
)
from .models import (
    ExecutionContext,
    ExecutionEvent,
    ExecutionEventType,
    ExecutionOutcome,
    ExecutionPlan,
    ExecutionResult,
    ExecutionSession,
    ExecutionStep,
    StepResult,
    StepStatus,
)
from .policy import ExecutionPolicy
from .ports import ExecutionAdapter, NoOpAdapter
from .registry import AdapterRegistry
from .store import InMemoryExecutionStore

__all__ = [
    "AdapterRegistry",
    "AdapterRegistryError",
    "ExecutionAdapter",
    "ExecutionContext",
    "ExecutionEngine",
    "ExecutionEngineError",
    "ExecutionEvent",
    "ExecutionEventType",
    "ExecutionOutcome",
    "ExecutionPlan",
    "ExecutionPolicy",
    "ExecutionPolicyError",
    "ExecutionResult",
    "ExecutionSession",
    "ExecutionStep",
    "ExecutionValidationError",
    "InMemoryExecutionStore",
    "NoOpAdapter",
    "StepResult",
    "StepStatus",
    "append_event",
    "create_session",
    "finish_session",
    "record_result",
]
