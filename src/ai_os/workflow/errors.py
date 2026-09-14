"""Workflow and state-machine exceptions."""

from __future__ import annotations

from collections.abc import Iterable


class WorkflowError(Exception):
    """Base error for executable workflow failures."""


class TransitionValidationError(WorkflowError):
    """Raised when transition metadata is incomplete."""


class InvalidTransitionError(WorkflowError):
    """Raised when the requested state transition is not permitted."""

    def __init__(self, source: str, target: str) -> None:
        self.source = source
        self.target = target
        super().__init__(f"Invalid task transition: {source} -> {target}")


class CompletionGateError(WorkflowError):
    """Raised when REVIEW to DONE completion gates do not pass."""

    def __init__(self, reasons: Iterable[str]) -> None:
        self.reasons = tuple(reasons)
        message = "; ".join(self.reasons) or "Completion gate failed"
        super().__init__(message)
