"""Tool-to-Adapter execution tests."""

from pathlib import Path

from ai_os.adapters import AdapterRegistry, AdapterService, AdapterStatus, ReadOnlyFileAdapter
from ai_os.agents import AgentRole, Capability, Permission
from ai_os.tasks import AcceptanceCriterion, Priority, Task, TaskStatus
from ai_os.tools import ToolInvocation, ToolRegistry, ToolService, core_tools


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
