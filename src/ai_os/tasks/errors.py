"""Task-domain exceptions."""

from __future__ import annotations

from collections.abc import Iterable


class TaskError(Exception):
    """Base error for task-domain failures."""


class TaskValidationError(TaskError):
    """Raised when a Task violates one or more schema constraints."""

    def __init__(self, issues: Iterable[str]) -> None:
        self.issues = tuple(issues)
        message = "; ".join(self.issues) or "Task validation failed"
        super().__init__(message)
