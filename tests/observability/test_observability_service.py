from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ai_os.observability import (
    ObservabilityService,
    RuntimeEvent,
    RuntimeEventSource,
    RuntimeEventType,
)
from ai_os.persistence import SQLiteRuntimeStore, StoreConfig


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
