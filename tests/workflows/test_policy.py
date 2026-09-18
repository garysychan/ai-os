"""Workflow default-deny policy tests."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from ai_os.tasks import AcceptanceCriterion, Priority, Task, TaskStatus
from ai_os.workflows import WorkflowPolicy, WorkflowPolicyError, coding_workflow

NOW = datetime(2026, 9, 18, tzinfo=UTC)


def task(status: TaskStatus = TaskStatus.IN_PROGRESS) -> Task:
    return Task(
        "TASK-0015",
        "Workflow Engine",
        Priority.P1,
        status,
        ("Developer", "Tester", "Reviewer", "Fixer"),
        ("TASK-0014",),
        (AcceptanceCriterion("workflow works", completed=True),),
    )


def authorize(item: Task, **kwargs: object) -> None:
    values = {
        "now": NOW,
        "deadline": NOW + timedelta(minutes=1),
        "approval_evidence": (),
        "max_fix_attempts": 2,
    }
    values.update(kwargs)
    WorkflowPolicy().authorize(
        item,
        coding_workflow(),
        {"TASK-0014": TaskStatus.DONE},
        **values,  # type: ignore[arg-type]
    )


def test_policy_enforces_state_dependencies_assignment_and_budget() -> None:
    authorize(task())
    with pytest.raises(WorkflowPolicyError, match="IN_PROGRESS"):
        authorize(task(TaskStatus.REVIEW))
    with pytest.raises(WorkflowPolicyError, match="not assigned"):
        authorize(replace(task(), agents=("Developer", "Tester", "Fixer")))
    with pytest.raises(WorkflowPolicyError, match="Fix Cycle budget"):
        authorize(task(), max_fix_attempts=3)
    with pytest.raises(WorkflowPolicyError, match="dependencies"):
        WorkflowPolicy().authorize(
            task(),
            coding_workflow(),
            {"TASK-0014": TaskStatus.REVIEW},
            now=NOW,
            deadline=None,
            approval_evidence=(),
            max_fix_attempts=2,
        )


def test_policy_enforces_deadline_and_approval() -> None:
    with pytest.raises(WorkflowPolicyError, match="expired"):
        authorize(task(), deadline=NOW)
    with pytest.raises(WorkflowPolicyError, match="timezone-aware"):
        authorize(task(), deadline=datetime(2026, 9, 18))
    with pytest.raises(WorkflowPolicyError, match="approval evidence"):
        definition = replace(coding_workflow(), approval_required=True)
        WorkflowPolicy().authorize(
            task(),
            definition,
            {"TASK-0014": TaskStatus.DONE},
            now=NOW,
            deadline=None,
            approval_evidence=(),
            max_fix_attempts=2,
        )
