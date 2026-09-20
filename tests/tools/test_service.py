"""Tool-to-Adapter execution tests."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ai_os.adapters import (
    AdapterRegistry,
    AdapterService,
    AdapterStatus,
    AdapterValidationError,
    ReadOnlyFileAdapter,
)
from ai_os.agents import AgentRole, Capability, Permission
from ai_os.tasks import AcceptanceCriterion, Priority, Task, TaskStatus
from ai_os.tools import (
    ToolInvocation,
    ToolPolicyError,
    ToolRegistry,
    ToolRegistryError,
    ToolService,
    core_tools,
)


def test_service_executes_only_through_shared_adapter_service(tmp_path: Path) -> None:
    target = tmp_path / "input.txt"
    target.write_text("governed", encoding="utf-8")
    adapters = AdapterRegistry((ReadOnlyFileAdapter((tmp_path,)),))
    service = ToolService(ToolRegistry(adapters, core_tools()), AdapterService(adapters))
    task = Task(
        "TASK-0014",
        "Tool Registry",
        Priority.P1,
        TaskStatus.IN_PROGRESS,
        ("Developer",),
        (),
        (AcceptanceCriterion("governed"),),
    )
    invocation = ToolInvocation(
        "invoke-1",
        task.task_id,
        "file",
        "1",
        "read_text",
        AgentRole.DEVELOPER,
        Capability.IMPLEMENT,
        Permission.MODIFY_CODE,
        (("path", str(target)),),
    )

    result = service.execute(task, invocation)

    assert result.adapter_result.status is AdapterStatus.SUCCESS
    assert dict(result.adapter_result.outputs)["content"] == "governed"
    assert result.audit.adapter == "file-read"


def test_service_rejects_different_adapter_registry_instances(tmp_path: Path) -> None:
    first = AdapterRegistry((ReadOnlyFileAdapter((tmp_path,)),))
    second = AdapterRegistry((ReadOnlyFileAdapter((tmp_path,)),))
    try:
        ToolService(ToolRegistry(first, core_tools()), AdapterService(second))
    except ValueError as error:
        assert "share one AdapterRegistry" in str(error)
    else:
        raise AssertionError("mismatched Adapter registries must fail closed")


def test_service_preserves_deadline_and_adapter_policy_rejects_expiry(tmp_path: Path) -> None:
    now = datetime(2026, 9, 17, tzinfo=UTC)
    target = tmp_path / "input.txt"
    target.write_text("governed", encoding="utf-8")
    adapters = AdapterRegistry((ReadOnlyFileAdapter((tmp_path,)),))
    service = ToolService(ToolRegistry(adapters, core_tools()), AdapterService(adapters))
    task = Task(
        "TASK-0014",
        "Tool Registry",
        Priority.P1,
        TaskStatus.IN_PROGRESS,
        ("Developer",),
        (),
        (AcceptanceCriterion("deadline is preserved"),),
    )
    invocation = ToolInvocation(
        "invoke-deadline",
        task.task_id,
        "file",
        "1",
        "read_text",
        AgentRole.DEVELOPER,
        Capability.IMPLEMENT,
        Permission.MODIFY_CODE,
        (("path", str(target)),),
        deadline=now + timedelta(seconds=1),
    )

    result = service.execute(task, invocation, clock=lambda: now)
    assert result.adapter_result.status is AdapterStatus.SUCCESS

    with pytest.raises(AdapterValidationError, match="deadline has expired"):
        service.execute(task, replace(invocation, deadline=now), clock=lambda: now)


def test_pre_execution_tool_denial_is_emitted_and_sink_failure_does_not_authorize(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 9, 20, tzinfo=UTC)
    adapters = AdapterRegistry((ReadOnlyFileAdapter((tmp_path,)),))
    denied: list[tuple[str, str]] = []
    service = ToolService(
        ToolRegistry(adapters, core_tools()),
        AdapterService(adapters),
        denial_sink=lambda invocation, _timestamp, reason: denied.append(
            (invocation.invocation_id, reason)
        ),
    )
    task = Task(
        "TASK-0017",
        "Observe denial",
        Priority.P1,
        TaskStatus.IN_PROGRESS,
        ("Developer",),
        (),
        (AcceptanceCriterion("denied"),),
    )
    invocation = ToolInvocation(
        "denied-1",
        task.task_id,
        "file",
        "1",
        "read_text",
        AgentRole.DEVELOPER,
        Capability.IMPLEMENT,
        Permission.READ_CONTROL,
        (("path", str(tmp_path / "missing")),),
    )
    with pytest.raises(ToolPolicyError):
        service.execute(task, invocation, clock=lambda: now)
    assert denied == [("denied-1", "ToolPolicyError")]

    with pytest.raises(ToolRegistryError):
        service.execute(task, replace(invocation, invocation_id="denied-2", operation="delete"))
    assert denied[-1] == ("denied-2", "ToolRegistryError")

    broken_sink = ToolService(
        ToolRegistry(adapters, core_tools()),
        AdapterService(adapters),
        denial_sink=lambda *_: (_ for _ in ()).throw(RuntimeError("sink failed")),
    )
    with pytest.raises(ToolPolicyError):
        broken_sink.execute(task, invocation, clock=lambda: now)
