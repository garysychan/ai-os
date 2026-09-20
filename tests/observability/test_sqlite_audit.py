from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ai_os.observability import (
    RuntimeEvent,
    RuntimeEventFilter,
    RuntimeEventSource,
    RuntimeEventType,
)
from ai_os.persistence import (
    CURRENT_SCHEMA_VERSION,
    PersistenceConfigurationError,
    PersistenceIntegrityError,
    SQLiteRuntimeStore,
    StoreConfig,
)

NOW = datetime(2026, 9, 20, tzinfo=UTC)


def event(sequence: int = 1, *, event_id: str | None = None) -> RuntimeEvent:
    return RuntimeEvent(
        event_id=event_id or f"event-{sequence}",
        sequence=sequence,
        timestamp=NOW + timedelta(seconds=sequence),
        event_type=(RuntimeEventType.STARTED if sequence == 1 else RuntimeEventType.COMPLETED),
        source=RuntimeEventSource.EXECUTION,
        task_id="TASK-0017",
        trace_id="trace-1",
        execution_id="execution-1",
        summary="token=private",
        evidence=("secret=private",),
    )


def store(path: Path) -> SQLiteRuntimeStore:
    item = SQLiteRuntimeStore(StoreConfig(path, max_query_limit=10))
    item.initialize()
    return item


def test_append_reopen_filter_and_redaction(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite3"
    first = store(database)
    first.append_runtime_event(event())
    first.append_runtime_event(event(2))

    reopened = SQLiteRuntimeStore(StoreConfig(database, max_query_limit=10))
    assert reopened.status().schema_version == CURRENT_SCHEMA_VERSION
    results = reopened.list_runtime_events(
        filters=RuntimeEventFilter(trace_id="trace-1", execution_id="execution-1"), limit=10
    )
    assert [item.sequence for item in results] == [1, 2]
    assert results[0].summary == "[REDACTED]"
    assert results[0].evidence == ("[REDACTED]",)
    assert reopened.get_runtime_event("event-2") == results[1]


def test_append_only_identity_and_ordering_fail_closed(tmp_path: Path) -> None:
    item = store(tmp_path / "runtime.sqlite3")
    item.append_runtime_event(event())
    with pytest.raises(PersistenceIntegrityError):
        item.append_runtime_event(event(event_id="duplicate-sequence"))
    with pytest.raises(PersistenceIntegrityError):
        item.append_runtime_event(replace(event(2), event_id="event-1"))
    with pytest.raises(PersistenceIntegrityError):
        item.append_runtime_event(event(3))


def test_queries_are_bounded_and_filters_are_validated(tmp_path: Path) -> None:
    item = store(tmp_path / "runtime.sqlite3")
    item.append_runtime_event(event())
    with pytest.raises(PersistenceConfigurationError):
        item.list_runtime_events(limit=11)
    with pytest.raises(PersistenceIntegrityError):
        item.list_runtime_events(filters=RuntimeEventFilter(trace_id=" "), limit=10)


def test_corrupt_and_unknown_schema_records_fail_closed(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite3"
    item = store(database)
    item.append_runtime_event(event())
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE runtime_events SET payload = ? WHERE event_id = ?",
            ('{"schema_version":99}', "event-1"),
        )
    with pytest.raises(PersistenceIntegrityError):
        item.get_runtime_event("event-1")


def test_prune_includes_runtime_events(tmp_path: Path) -> None:
    item = store(tmp_path / "runtime.sqlite3")
    item.append_runtime_event(event())
    result = item.prune(before=NOW + timedelta(days=1), limit=10)
    assert result.runtime_events == 1
    assert item.status().runtime_events == 0


def test_store_allocates_global_sequence_and_trace_orders_by_sequence(tmp_path: Path) -> None:
    item = store(tmp_path / "runtime.sqlite3")
    later_clock = replace(event(), sequence=0, timestamp=NOW + timedelta(hours=1))
    earlier_clock = replace(
        event(2, event_id="event-2"), sequence=0, timestamp=NOW - timedelta(hours=1)
    )
    assert item.append_runtime_event(later_clock).sequence == 1
    assert item.append_runtime_event(earlier_clock).sequence == 2
    assert [
        entry.event_id
        for entry in item.list_runtime_events(
            filters=RuntimeEventFilter(trace_id="trace-1"), limit=10
        )
    ] == ["event-1", "event-2"]


def test_same_trace_concurrent_writers_receive_unique_sequences(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite3"
    store(database)

    def append(index: int) -> int:
        writer = SQLiteRuntimeStore(StoreConfig(database, busy_timeout_ms=10_000))
        candidate = replace(
            event(), event_id=f"concurrent-{index}", sequence=0, trace_id="trace-concurrent"
        )
        return writer.append_runtime_event(candidate).sequence

    with ThreadPoolExecutor(max_workers=16) as executor:
        sequences = tuple(executor.map(append, range(32)))

    assert sorted(sequences) == list(range(1, 33))
    reader = SQLiteRuntimeStore(StoreConfig(database))
    assert (
        len(
            reader.list_runtime_events(
                filters=RuntimeEventFilter(trace_id="trace-concurrent"), limit=100
            )
        )
        == 32
    )
