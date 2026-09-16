"""Persistent Runtime Store integration and failure-path tests."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from ai_os.adapters import AdapterAuditEvent, AdapterStatus
from ai_os.agents import AgentRole, Capability, Permission
from ai_os.controller import (
    ControllerEventType,
    ControllerSession,
    ControllerStage,
    TraceEvent,
)
from ai_os.execution import (
    ExecutionEvent,
    ExecutionEventType,
    ExecutionPlan,
    ExecutionSession,
    ExecutionStep,
)
from ai_os.persistence import (
    CURRENT_SCHEMA_VERSION,
    PersistenceConfigurationError,
    PersistenceIntegrityError,
    PersistenceMigrationError,
    PersistenceNotFoundError,
    SQLiteRuntimeStore,
    StoreConfig,
)
from ai_os.tasks import TaskStatus

NOW = datetime(2026, 9, 16, tzinfo=UTC)


def controller_session() -> ControllerSession:
    event = TraceEvent(
        sequence=1,
        session_id="controller-1",
        task_id="TASK-0013",
        event_type=ControllerEventType.SESSION_STARTED,
        stage=ControllerStage.CREATED,
        actor=AgentRole.CONTROLLER,
        timestamp=NOW,
        reason="persistent session",
        evidence=("CR-2026-010 APPROVED",),
    )
    return ControllerSession(
        session_id="controller-1",
        task_id="TASK-0013",
        objective="persist runtime evidence",
        stage=ControllerStage.CREATED,
        task_status=TaskStatus.IN_PROGRESS,
        started_at=NOW,
        updated_at=NOW,
        max_fix_attempts=2,
        events=(event,),
    )


def execution_plan() -> ExecutionPlan:
    return ExecutionPlan(
        plan_id="plan-1",
        task_id="TASK-0013",
        steps=(
            ExecutionStep(
                step_id="step-1",
                adapter="memory",
                operation="record",
                agent_role=AgentRole.DEVELOPER,
                capability=Capability.IMPLEMENT,
                required_permission=Permission.MODIFY_CODE,
                inputs=(("value", "safe"),),
            ),
        ),
        max_steps=1,
    )


def execution_session() -> ExecutionSession:
    event = ExecutionEvent(
        sequence=1,
        execution_id="execution-1",
        task_id="TASK-0013",
        event_type=ExecutionEventType.SESSION_STARTED,
        timestamp=NOW,
        reason="persistent execution",
    )
    return ExecutionSession(
        execution_id="execution-1",
        plan_id="plan-1",
        task_id="TASK-0013",
        controller_session_id="controller-1",
        started_at=NOW,
        updated_at=NOW,
        events=(event,),
    )


def audit_event(*, sequence: int = 1) -> AdapterAuditEvent:
    return AdapterAuditEvent(
        sequence=sequence,
        invocation_id="invocation-1",
        task_id="TASK-0013",
        adapter="file-read",
        operation="read_text",
        timestamp=NOW,
        status=AdapterStatus.SUCCESS,
        evidence=("path=safe.txt",),
    )


def test_initialize_status_and_deterministic_round_trip(tmp_path: pytest.TempPathFactory) -> None:
    database = tmp_path / "runtime.sqlite"
    store = SQLiteRuntimeStore(StoreConfig(database=database))
    status = store.initialize()
    assert status.initialized
    assert status.schema_version == CURRENT_SCHEMA_VERSION
    assert database.stat().st_mode & 0o777 == 0o600

    store.save_controller_session(controller_session())
    store.save_execution_bundle(execution_plan(), execution_session())
    store.append_adapter_audit(audit_event())

    reopened = SQLiteRuntimeStore(StoreConfig(database=database))
    assert reopened.get_controller_session("controller-1") == controller_session()
    assert reopened.get_execution_plan("plan-1") == execution_plan()
    assert reopened.get_execution_session("execution-1") == execution_session()
    assert reopened.list_adapter_audit(invocation_id="invocation-1") == (audit_event(),)
    counts = reopened.status()
    assert counts.controller_sessions == 1
    assert counts.execution_plans == 1
    assert counts.execution_sessions == 1
    assert counts.adapter_audit_events == 1


def test_store_redacts_sensitive_text_before_persistence(tmp_path: pytest.TempPathFactory) -> None:
    database = tmp_path / "runtime.sqlite"
    store = SQLiteRuntimeStore(StoreConfig(database=database))
    store.initialize()
    unsafe = replace(
        audit_event(),
        evidence=("authorization=Bearer-secret", "token:abc123"),
    )
    store.append_adapter_audit(unsafe)
    stored = store.list_adapter_audit()[0]
    assert stored.evidence == ("authorization=[REDACTED]", "token=[REDACTED]")
    assert "Bearer-secret" not in database.read_bytes().decode(errors="ignore")


def test_unknown_schema_corrupt_record_and_missing_record_fail_closed(
    tmp_path: pytest.TempPathFactory,
) -> None:
    database = tmp_path / "runtime.sqlite"
    store = SQLiteRuntimeStore(StoreConfig(database=database))
    store.initialize()
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO controller_sessions VALUES (?, ?, ?, ?)",
            ("broken", "TASK-0013", NOW.isoformat(), "not-json"),
        )
    with pytest.raises(PersistenceIntegrityError):
        store.get_controller_session("broken")
    with pytest.raises(PersistenceNotFoundError):
        store.get_controller_session("missing")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
            (CURRENT_SCHEMA_VERSION + 1, NOW.isoformat()),
        )
    with pytest.raises(PersistenceMigrationError):
        store.status()


def test_atomic_bundle_rolls_back_and_audit_is_append_only(
    tmp_path: pytest.TempPathFactory,
) -> None:
    store = SQLiteRuntimeStore(StoreConfig(database=tmp_path / "runtime.sqlite"))
    store.initialize()
    mismatch = replace(execution_session(), plan_id="different")
    with pytest.raises(PersistenceIntegrityError):
        store.save_execution_bundle(execution_plan(), mismatch)
    assert store.status().execution_plans == 0
    assert store.status().execution_sessions == 0
    store.append_adapter_audit(audit_event())
    with pytest.raises(PersistenceIntegrityError):
        store.append_adapter_audit(audit_event())


def test_path_policy_sequence_and_query_bounds(tmp_path: pytest.TempPathFactory) -> None:
    with pytest.raises(PersistenceConfigurationError):
        SQLiteRuntimeStore(StoreConfig(database=tmp_path / "TASKS.md"))
    denied = tmp_path / "denied.sqlite"
    with pytest.raises(PersistenceConfigurationError):
        SQLiteRuntimeStore(StoreConfig(database=denied, denied_paths=(denied,)))
    target = tmp_path / "target.sqlite"
    target.touch()
    symlink = tmp_path / "runtime-link.sqlite"
    symlink.symlink_to(target)
    with pytest.raises(PersistenceConfigurationError):
        SQLiteRuntimeStore(StoreConfig(database=symlink))

    store = SQLiteRuntimeStore(StoreConfig(database=tmp_path / "runtime.sqlite", max_query_limit=2))
    assert store.status().initialized is False
    store.initialize()
    invalid = replace(
        controller_session(),
        events=(replace(controller_session().events[0], sequence=2),),
    )
    with pytest.raises(PersistenceIntegrityError):
        store.save_controller_session(invalid)
    with pytest.raises(PersistenceConfigurationError):
        store.list_adapter_audit(limit=3)


def test_prune_is_bounded_and_transactional(tmp_path: pytest.TempPathFactory) -> None:
    store = SQLiteRuntimeStore(StoreConfig(database=tmp_path / "runtime.sqlite"))
    store.initialize()
    store.save_controller_session(controller_session())
    store.save_execution_bundle(execution_plan(), execution_session())
    store.append_adapter_audit(audit_event())
    result = store.prune(before=NOW + timedelta(seconds=1), limit=1)
    assert result.controller_sessions == 1
    assert result.execution_sessions == 1
    assert result.execution_plans == 1
    assert result.adapter_audit_events == 1
    assert store.status().controller_sessions == 0


def test_payload_is_canonical_json(tmp_path: pytest.TempPathFactory) -> None:
    database = tmp_path / "runtime.sqlite"
    store = SQLiteRuntimeStore(StoreConfig(database=database))
    store.initialize()
    store.save_execution_plan(execution_plan())
    with sqlite3.connect(database) as connection:
        payload = connection.execute("SELECT payload FROM execution_plans").fetchone()[0]
    decoded = json.loads(payload)
    assert decoded["codec_version"] == 1
    assert decoded["kind"] == "execution_plan"


def test_independent_connections_serialize_concurrent_writes(
    tmp_path: pytest.TempPathFactory,
) -> None:
    database = tmp_path / "runtime.sqlite"
    SQLiteRuntimeStore(StoreConfig(database=database)).initialize()

    def save(index: int) -> None:
        store = SQLiteRuntimeStore(StoreConfig(database=database, busy_timeout_ms=2_000))
        store.save_controller_session(
            replace(
                controller_session(),
                session_id=f"controller-{index}",
                events=(
                    replace(
                        controller_session().events[0],
                        session_id=f"controller-{index}",
                    ),
                ),
            )
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        tuple(executor.map(save, range(8)))
    assert SQLiteRuntimeStore(StoreConfig(database=database)).status().controller_sessions == 8
