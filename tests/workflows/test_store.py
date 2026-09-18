"""Persistent Workflow session store tests."""

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_os.workflows import (
    JsonWorkflowStore,
    WorkflowEvent,
    WorkflowSession,
    WorkflowStatus,
    WorkflowValidationError,
)

NOW = datetime(2026, 9, 18, tzinfo=UTC)


def session() -> WorkflowSession:
    session_id = "workflow:TASK-0015:coding:1:1"
    event = WorkflowEvent(
        1,
        session_id,
        "TASK-0015",
        "WORKFLOW_STARTED",
        "CREATED",
        NOW,
        "started",
        ("CR-2026-012",),
    )
    return WorkflowSession(
        session_id,
        "TASK-0015",
        "coding",
        "1",
        "validate persistence",
        WorkflowStatus.CREATED,
        NOW,
        NOW,
        None,
        8,
        2,
        ("CR-2026-012",),
        (event,),
    )


def test_json_store_round_trip_and_update(tmp_path: Path) -> None:
    store = JsonWorkflowStore(tmp_path / "sessions")
    created = session()
    store.save(created)
    assert store.get(created.session_id) == created
    completed = replace(created, status=WorkflowStatus.COMPLETED)
    store.save(completed)
    assert store.get(created.session_id) == completed


def test_json_store_rejects_missing_corrupt_and_wrong_identity(tmp_path: Path) -> None:
    store = JsonWorkflowStore(tmp_path)
    with pytest.raises(WorkflowValidationError, match="unknown"):
        store.get("missing")

    created = session()
    store.save(created)
    document = next(tmp_path.glob("*.json"))
    document.write_text("not json", encoding="utf-8")
    with pytest.raises(WorkflowValidationError, match="corrupt"):
        store.get(created.session_id)

    store.save(created)
    payload = json.loads(document.read_text(encoding="utf-8"))
    payload["session_id"] = "different"
    document.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(WorkflowValidationError, match="identity"):
        store.get(created.session_id)
