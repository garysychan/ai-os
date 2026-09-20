from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from ai_os.observability import RuntimeEvent, RuntimeEventSource, RuntimeEventType
from ai_os.persistence import SQLiteRuntimeStore, StoreConfig


def seed(database: Path) -> None:
    store = SQLiteRuntimeStore(StoreConfig(database))
    store.initialize()
    store.append_runtime_event(
        RuntimeEvent(
            event_id="event-1",
            sequence=1,
            timestamp=datetime(2026, 9, 20, tzinfo=UTC),
            event_type=RuntimeEventType.COMPLETED,
            source=RuntimeEventSource.WORKFLOW,
            task_id="TASK-0017",
            trace_id="trace-1",
            summary="complete",
        )
    )


def run_cli(*args: str) -> tuple[int, dict[str, object]]:
    source = Path(__file__).parents[1]
    completed = subprocess.run(
        [sys.executable, "-m", "ai_os.cli", *args],
        check=False,
        capture_output=True,
        text=True,
        env=os.environ | {"PYTHONPATH": str(source / "src")},
    )
    return completed.returncode, json.loads(completed.stdout)


def test_cross_process_audit_and_trace_inspection(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite3"
    seed(database)
    code, audit = run_cli(
        "audit",
        "list",
        "--database",
        str(database),
        "--task-id",
        "TASK-0017",
        "--actor-role",
        "Reviewer",
        "--json",
    )
    assert code == 0
    assert audit["status"] == "PASS"
    assert len(audit["events"]) == 1  # type: ignore[arg-type]

    code, trace = run_cli(
        "trace",
        "show",
        "trace-1",
        "--database",
        str(database),
        "--actor-role",
        "Reviewer",
        "--json",
    )
    assert code == 0
    assert trace["events"][0]["event_id"] == "event-1"  # type: ignore[index]


def test_cli_unknown_event_fails_closed(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite3"
    seed(database)
    code, payload = run_cli(
        "audit",
        "show",
        "missing",
        "--database",
        str(database),
        "--actor-role",
        "Reviewer",
        "--json",
    )
    assert code == 2
    assert payload["status"] == "FAIL"

    code, payload = run_cli(
        "trace",
        "show",
        "missing",
        "--database",
        str(database),
        "--actor-role",
        "Reviewer",
        "--json",
    )
    assert code == 2
    assert payload["status"] == "FAIL"
