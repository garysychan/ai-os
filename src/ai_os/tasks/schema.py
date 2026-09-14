"""Validation for the canonical AI OS Task Schema."""

from __future__ import annotations

import re

from .errors import TaskValidationError
from .models import Priority, Task, TaskStatus

_TASK_ID_RE = re.compile(r"^TASK-\d{4,}$")


def validation_issues(task: Task) -> tuple[str, ...]:
    """Return every deterministic schema violation for a Task."""
    issues: list[str] = []

    if not isinstance(task.priority, Priority):
        issues.append("priority must be a Priority enum")
    if not isinstance(task.status, TaskStatus):
        issues.append("status must be a TaskStatus enum")
    if not _TASK_ID_RE.fullmatch(task.task_id):
        issues.append("task_id must match TASK- followed by at least four digits")
    if not task.title.strip():
        issues.append("title must not be empty")
    if not task.agents:
        issues.append("at least one Agent must be assigned")
    elif any(not agent.strip() for agent in task.agents):
        issues.append("Agent names must not be empty")
    if task.task_id in task.dependencies:
        issues.append("a Task cannot depend on itself")
    if len(set(task.dependencies)) != len(task.dependencies):
        issues.append("dependencies must not contain duplicates")
    if any(not dependency.strip() for dependency in task.dependencies):
        issues.append("dependency IDs must not be empty")
    if not task.acceptance_criteria:
        issues.append("acceptance_criteria must not be empty")
    for index, criterion in enumerate(task.acceptance_criteria, start=1):
        if not criterion.description.strip():
            issues.append(
                f"acceptance criterion {index} description must not be empty"
            )
    if task.status is TaskStatus.DONE and not task.completion_evidence:
        issues.append("a DONE Task must include completion_evidence")

    return tuple(issues)


def validate_task(task: Task) -> Task:
    """Return the Task when valid; otherwise raise all schema violations."""
    issues = validation_issues(task)
    if issues:
        raise TaskValidationError(issues)
    return task
