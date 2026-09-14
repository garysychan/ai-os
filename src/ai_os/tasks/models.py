"""Canonical immutable Task Schema for the AI OS V2 runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TaskStatus(str, Enum):
    """Executable task lifecycle states."""

    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    REVIEW = "REVIEW"
    DONE = "DONE"


class Priority(str, Enum):
    """Task scheduling priority."""

    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class ReviewResult(str, Enum):
    """Normalized Reviewer outcomes."""

    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class AcceptanceCriterion:
    """One measurable task completion condition."""

    description: str
    completed: bool = False
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class Task:
    """The single canonical runtime representation of an AI OS task."""

    task_id: str
    title: str
    priority: Priority
    status: TaskStatus
    agents: tuple[str, ...]
    dependencies: tuple[str, ...]
    acceptance_criteria: tuple[AcceptanceCriterion, ...]
    completion_evidence: tuple[str, ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()
