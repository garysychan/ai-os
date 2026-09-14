"""Executable workflow and task state-machine services."""

from .errors import (
    CompletionGateError,
    InvalidTransitionError,
    TransitionValidationError,
    WorkflowError,
)
from .state_machine import (
    StateMachine,
    TransitionContext,
    TransitionEvent,
    completion_gate_failures,
)
from .transitions import (
    ALLOWED_TRANSITIONS,
    Transition,
    is_valid_transition,
    normalize_status,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "CompletionGateError",
    "InvalidTransitionError",
    "StateMachine",
    "Transition",
    "TransitionContext",
    "TransitionEvent",
    "TransitionValidationError",
    "WorkflowError",
    "completion_gate_failures",
    "is_valid_transition",
    "normalize_status",
]
