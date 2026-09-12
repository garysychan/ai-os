"""Executable task-state transition policy."""

from __future__ import annotations

ALLOWED_TRANSITIONS = frozenset(
    {
        ("TODO", "IN_PROGRESS"),
        ("TODO", "BLOCKED"),
        ("IN_PROGRESS", "REVIEW"),
        ("IN_PROGRESS", "BLOCKED"),
        ("REVIEW", "IN_PROGRESS"),
        ("REVIEW", "DONE"),
        ("REVIEW", "BLOCKED"),
        ("BLOCKED", "TODO"),
        ("BLOCKED", "IN_PROGRESS"),
    }
)


def is_valid_transition(source: str, target: str) -> bool:
    """Return whether a task transition is permitted by the V2 policy."""
    return (source, target) in ALLOWED_TRANSITIONS
