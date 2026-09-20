from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ai_os.adapters import AdapterInvocation, AdapterRegistry, AdapterService, ReadOnlyFileAdapter
from ai_os.agents import AgentRole, Capability, Permission
from ai_os.observability import (
    ObservabilityService,
    RuntimeEvent,
    RuntimeEventSource,
    RuntimeEventType,
)
from ai_os.persistence import SQLiteRuntimeStore, StoreConfig
from ai_os.tasks import AcceptanceCriterion, Priority, Task, TaskStatus


def test_service_records_and_reconstructs_read_only_trace(tmp_path: Path) -> None:
    store = SQLiteRuntimeStore(StoreConfig(tmp_path / "runtime.sqlite3"))
    store.initialize()
    service = ObservabilityService(store)
    recorded = service.record(
        RuntimeEvent(
            event_id="event-1",
            sequence=1,
            timestamp=datetime(2026, 9, 20, tzinfo=UTC),
            event_type=RuntimeEventType.DENIED,
            source=RuntimeEventSource.GOVERNANCE,
            task_id="TASK-0017",
            trace_id="trace-1",
            summary="permission denied",
            agent_role="Developer",
        )
    )
    assert service.get(recorded.event_id) == recorded
    assert service.trace("trace-1") == (recorded,)


def test_real_adapter_boundary_persists_correlated_redacted_event(tmp_path: Path) -> None:
    database = SQLiteRuntimeStore(StoreConfig(tmp_path / "runtime.sqlite3"))
    database.initialize()
    observability = ObservabilityService(database)
    target = tmp_path / "input.txt"
    target.write_text("safe", encoding="utf-8")
    adapter = AdapterService(
        AdapterRegistry((ReadOnlyFileAdapter((tmp_path,)),)),
        audit_sink=observability.adapter_sink("trace-runtime"),
    )
    task = Task(
        "TASK-0017",
        "Observe",
        Priority.P1,
        TaskStatus.IN_PROGRESS,
        ("Developer",),
        (),
        (AcceptanceCriterion("audited"),),
    )
    invocation = AdapterInvocation(
        "invocation-1",
        task.task_id,
        "file-read",
        "1",
        "read_text",
        AgentRole.DEVELOPER,
        Capability.IMPLEMENT,
        Permission.MODIFY_CODE,
        (("path", str(target)), ("token", "never-store")),
    )
    result, _ = adapter.execute(task, invocation)
    assert result.summary
    events = observability.trace("trace-runtime")
    assert len(events) == 1
    assert events[0].invocation_id == "invocation-1"
    assert "never-store" not in repr(events)
