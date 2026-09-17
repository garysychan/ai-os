"""Default-deny Tool policy tests."""

from dataclasses import replace

import pytest

from ai_os.agents import AgentRole, Capability, Permission
from ai_os.tasks import AcceptanceCriterion, Priority, Task, TaskStatus
from ai_os.tools import ToolInvocation, ToolPolicy, ToolPolicyError, core_tools


def task(status: TaskStatus = TaskStatus.IN_PROGRESS) -> Task:
    return Task(
        "TASK-0014",
        "Tool Registry",
        Priority.P1,
        status,
        ("Developer",),
        (),
        (AcceptanceCriterion("governed"),),
    )


def invocation() -> ToolInvocation:
    return ToolInvocation(
        "invoke-1",
        "TASK-0014",
        "file",
        "1",
        "read_text",
        AgentRole.DEVELOPER,
        Capability.IMPLEMENT,
        Permission.MODIFY_CODE,
    )


def test_policy_enforces_state_assignment_capability_and_permission() -> None:
    policy = ToolPolicy()
    operation = core_tools()[0].operations[0]
    policy.authorize(task(), operation, invocation())
    with pytest.raises(ToolPolicyError, match="IN_PROGRESS"):
        policy.authorize(task(TaskStatus.REVIEW), operation, invocation())
    with pytest.raises(ToolPolicyError, match="not assigned"):
        policy.authorize(task(), operation, replace(invocation(), agent_role=AgentRole.RESEARCHER))
    with pytest.raises(ToolPolicyError, match="capability"):
        policy.authorize(task(), operation, replace(invocation(), capability=Capability.REVIEW))
    with pytest.raises(ToolPolicyError, match="permission"):
        policy.authorize(
            task(), operation, replace(invocation(), required_permission=Permission.READ_CONTROL)
        )


def test_policy_requires_evidence_when_operation_requires_approval() -> None:
    policy = ToolPolicy()
    operation = replace(core_tools()[0].operations[0], approval_required=True)
    with pytest.raises(ToolPolicyError, match="approval evidence"):
        policy.authorize(task(), operation, invocation())
    policy.authorize(
        task(), operation, replace(invocation(), approval_evidence=("APPROVE CR-2026-011",))
    )
