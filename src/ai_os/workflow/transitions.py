"""Executable task-state transition policy."""

from __future__ import annotations

from ai_os.tasks.models import TaskStatus

Transition = tuple[TaskStatus, TaskStatus]

ALLOWED_TRANSITIONS: frozenset[Transition] = frozenset(
    {
        (TaskStatus.TODO, TaskStatus.IN_PROGRESS),
        (TaskStatus.TODO, TaskStatus.BLOCKED),
        (TaskStatus.IN_PROGRESS, TaskStatus.REVIEW),
        (TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED),
        (TaskStatus.REVIEW, TaskStatus.IN_PROGRESS),
        (TaskStatus.REVIEW, TaskStatus.BLOCKED),
        (TaskStatus.REVIEW, TaskStatus.DONE),
        (TaskStatus.BLOCKED, TaskStatus.TODO),
        (TaskStatus.BLOCKED, TaskStatus.IN_PROGRESS),
    }
)


def normalize_status(value: TaskStatus | str) -> TaskStatus:
    """Normalize an enum or exact state string to TaskStatus."""
    if isinstance(value, TaskStatus):
        return value
    return TaskStatus(value)


def is_valid_transition(
    source: TaskStatus | str,
    target: TaskStatus | str,
) -> bool:
    """Return whether the requested transition is allowed."""
    try:
        normalized = (normalize_status(source), normalize_status(target))
    except ValueError:
        return False
    return normalized in ALLOWED_TRANSITIONS
