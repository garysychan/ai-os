"""Governed SQLite Persistent Runtime Store."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from ai_os.adapters import AdapterAuditEvent
from ai_os.controller import ControllerSession
from ai_os.execution import ExecutionPlan, ExecutionSession

from .codecs import (
    dump_adapter_audit,
    dump_controller_session,
    dump_execution_plan,
    dump_execution_session,
    load_adapter_audit,
    load_controller_session,
    load_execution_plan,
    load_execution_session,
)
from .errors import (
    PersistenceConfigurationError,
    PersistenceError,
    PersistenceIntegrityError,
    PersistenceMigrationError,
    PersistenceNotFoundError,
)
from .migrations import CURRENT_SCHEMA_VERSION, MIGRATIONS
from .models import PruneResult, StoreConfig, StoreStatus

_CONTROL_FILES = {
    "CONTROL_PLANE.md",
    "AGENTS.md",
    "PROJECT_RULES.md",
    "ARCHITECTURE.md",
    "WORKFLOW.md",
    "TASKS.md",
}


class SQLiteRuntimeStore:
    """Explicit SQLite adapter; construction performs no filesystem writes."""

    def __init__(self, config: StoreConfig) -> None:
        self.config = config
        self.database = self._validate_path(config)
        if config.busy_timeout_ms < 0:
            raise PersistenceConfigurationError("busy_timeout_ms must be non-negative")
        if config.max_query_limit < 1:
            raise PersistenceConfigurationError("max_query_limit must be positive")

    @staticmethod
    def _validate_path(config: StoreConfig) -> Path:
        supplied = config.database.expanduser()
        if supplied.name in _CONTROL_FILES:
            raise PersistenceConfigurationError("database cannot target a Control Plane file")
        if supplied.is_symlink():
            raise PersistenceConfigurationError("database path cannot be a symlink")
        lexical = supplied.absolute()
        if any(item.exists() and item.is_symlink() for item in (lexical, *lexical.parents)):
            raise PersistenceConfigurationError("database path cannot traverse a symlink")
        if supplied.exists() and not supplied.is_file():
            raise PersistenceConfigurationError("database path must be a regular file")
        resolved = supplied.resolve(strict=False)
        for denied in config.denied_paths:
            denied_resolved = denied.expanduser().resolve(strict=False)
            if resolved == denied_resolved:
                raise PersistenceConfigurationError("database path is explicitly denied")
        return resolved

    def initialize(self) -> StoreStatus:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.migrate()
        return self.status()

    def migrate(self) -> StoreStatus:
        self.database.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._connect(create=True) as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    connection.execute(
                        "CREATE TABLE IF NOT EXISTS schema_migrations ("
                        "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
                    )
                    current = self._schema_version(connection)
                    if current > CURRENT_SCHEMA_VERSION:
                        raise PersistenceMigrationError(
                            f"database schema {current} is newer than supported "
                            f"{CURRENT_SCHEMA_VERSION}"
                        )
                    for version in range(current + 1, CURRENT_SCHEMA_VERSION + 1):
                        statements = MIGRATIONS.get(version)
                        if statements is None:
                            raise PersistenceMigrationError(
                                f"missing migration for schema version {version}"
                            )
                        for statement in statements:
                            connection.execute(statement)
                        connection.execute(
                            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                            (version, datetime.now().astimezone().isoformat()),
                        )
                except Exception:
                    connection.rollback()
                    raise
                else:
                    connection.commit()
        except sqlite3.DatabaseError as error:
            raise PersistenceMigrationError("SQLite migration failed") from error
        self._secure_permissions()
        return self.status()

    def status(self) -> StoreStatus:
        if not self.database.exists():
            return StoreStatus(
                database=self.database,
                initialized=False,
                schema_version=0,
                current_schema_version=CURRENT_SCHEMA_VERSION,
                controller_sessions=0,
                execution_plans=0,
                execution_sessions=0,
                adapter_audit_events=0,
            )
        try:
            with self._connect(create=False) as connection:
                version = self._schema_version(connection)
                if version > CURRENT_SCHEMA_VERSION:
                    raise PersistenceMigrationError(
                        f"database schema {version} is newer than supported "
                        f"{CURRENT_SCHEMA_VERSION}"
                    )
                initialized = version == CURRENT_SCHEMA_VERSION
                counts = {
                    table: self._count(connection, table) if initialized else 0
                    for table in (
                        "controller_sessions",
                        "execution_plans",
                        "execution_sessions",
                        "adapter_audit_events",
                    )
                }
        except sqlite3.DatabaseError as error:
            raise PersistenceIntegrityError("cannot inspect SQLite database") from error
        return StoreStatus(
            database=self.database,
            initialized=initialized,
            schema_version=version,
            current_schema_version=CURRENT_SCHEMA_VERSION,
            controller_sessions=counts["controller_sessions"],
            execution_plans=counts["execution_plans"],
            execution_sessions=counts["execution_sessions"],
            adapter_audit_events=counts["adapter_audit_events"],
        )

    def save_controller_session(self, session: ControllerSession) -> None:
        self._validate_ordered_sequences(event.sequence for event in session.events)
        payload = dump_controller_session(session)
        self._execute_write(
            """INSERT INTO controller_sessions(session_id, task_id, updated_at, payload)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                 task_id=excluded.task_id,
                 updated_at=excluded.updated_at,
                 payload=excluded.payload""",
            (session.session_id, session.task_id, session.updated_at.isoformat(), payload),
        )

    def get_controller_session(self, session_id: str) -> ControllerSession:
        payload = self._get_payload("controller_sessions", "session_id", session_id)
        session = load_controller_session(payload)
        if session.session_id != session_id:
            raise PersistenceIntegrityError("controller session identifier mismatch")
        return session

    def save_execution_plan(self, plan: ExecutionPlan) -> None:
        payload = dump_execution_plan(plan)
        self._execute_write(
            """INSERT INTO execution_plans(plan_id, task_id, updated_at, payload)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(plan_id) DO UPDATE SET
                 task_id=excluded.task_id,
                 updated_at=excluded.updated_at,
                 payload=excluded.payload""",
            (plan.plan_id, plan.task_id, self._now(), payload),
        )

    def get_execution_plan(self, plan_id: str) -> ExecutionPlan:
        payload = self._get_payload("execution_plans", "plan_id", plan_id)
        plan = load_execution_plan(payload)
        if plan.plan_id != plan_id:
            raise PersistenceIntegrityError("execution plan identifier mismatch")
        return plan

    def save_execution_session(self, session: ExecutionSession) -> None:
        self._validate_ordered_sequences(event.sequence for event in session.events)
        payload = dump_execution_session(session)
        self._execute_write(
            """INSERT INTO execution_sessions(
                 execution_id, plan_id, task_id, updated_at, payload
               ) VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(execution_id) DO UPDATE SET
                 plan_id=excluded.plan_id,
                 task_id=excluded.task_id,
                 updated_at=excluded.updated_at,
                 payload=excluded.payload""",
            (
                session.execution_id,
                session.plan_id,
                session.task_id,
                session.updated_at.isoformat(),
                payload,
            ),
        )

    def save_execution_bundle(self, plan: ExecutionPlan, session: ExecutionSession) -> None:
        """Atomically persist a related plan and session."""
        if plan.plan_id != session.plan_id or plan.task_id != session.task_id:
            raise PersistenceIntegrityError("execution plan and session do not match")
        self._validate_ordered_sequences(event.sequence for event in session.events)
        with self._ready_connection() as connection:
            try:
                with connection:
                    connection.execute(
                        """INSERT INTO execution_plans(plan_id, task_id, updated_at, payload)
                           VALUES (?, ?, ?, ?)
                           ON CONFLICT(plan_id) DO UPDATE SET
                             task_id=excluded.task_id, updated_at=excluded.updated_at,
                             payload=excluded.payload""",
                        (
                            plan.plan_id,
                            plan.task_id,
                            session.updated_at.isoformat(),
                            dump_execution_plan(plan),
                        ),
                    )
                    connection.execute(
                        """INSERT INTO execution_sessions(
                             execution_id, plan_id, task_id, updated_at, payload
                           ) VALUES (?, ?, ?, ?, ?)
                           ON CONFLICT(execution_id) DO UPDATE SET
                             plan_id=excluded.plan_id, task_id=excluded.task_id,
                             updated_at=excluded.updated_at, payload=excluded.payload""",
                        (
                            session.execution_id,
                            session.plan_id,
                            session.task_id,
                            session.updated_at.isoformat(),
                            dump_execution_session(session),
                        ),
                    )
            except sqlite3.DatabaseError as error:
                raise PersistenceIntegrityError("execution bundle transaction failed") from error

    def get_execution_session(self, execution_id: str) -> ExecutionSession:
        payload = self._get_payload("execution_sessions", "execution_id", execution_id)
        session = load_execution_session(payload)
        if session.execution_id != execution_id:
            raise PersistenceIntegrityError("execution session identifier mismatch")
        return session

    def append_adapter_audit(self, event: AdapterAuditEvent) -> None:
        if event.sequence < 1:
            raise PersistenceIntegrityError("adapter audit sequence must be positive")
        self._execute_write(
            """INSERT INTO adapter_audit_events(
                 invocation_id, sequence, task_id, timestamp, payload
               ) VALUES (?, ?, ?, ?, ?)""",
            (
                event.invocation_id,
                event.sequence,
                event.task_id,
                event.timestamp.isoformat(),
                dump_adapter_audit(event),
            ),
        )

    def list_adapter_audit(
        self, *, invocation_id: str | None = None, limit: int = 100
    ) -> tuple[AdapterAuditEvent, ...]:
        bounded = self._bounded_limit(limit)
        with self._ready_connection() as connection:
            if invocation_id is None:
                rows = connection.execute(
                    "SELECT payload FROM adapter_audit_events "
                    "ORDER BY timestamp, invocation_id, sequence LIMIT ?",
                    (bounded,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT payload FROM adapter_audit_events WHERE invocation_id = ? "
                    "ORDER BY sequence LIMIT ?",
                    (invocation_id, bounded),
                ).fetchall()
        return tuple(load_adapter_audit(row[0]) for row in rows)

    def prune(self, *, before: datetime, limit: int = 100) -> PruneResult:
        if before.tzinfo is None or before.utcoffset() is None:
            raise PersistenceIntegrityError("prune timestamp must be timezone-aware")
        bounded = self._bounded_limit(limit)
        cutoff = before.isoformat()
        with self._ready_connection() as connection:
            try:
                with connection:
                    controller = self._delete_limited(
                        connection, "controller_sessions", "updated_at", cutoff, bounded
                    )
                    execution = self._delete_limited(
                        connection, "execution_sessions", "updated_at", cutoff, bounded
                    )
                    audit = self._delete_limited(
                        connection, "adapter_audit_events", "timestamp", cutoff, bounded
                    )
                    plans = connection.execute(
                        "DELETE FROM execution_plans WHERE plan_id IN ("
                        "SELECT p.plan_id FROM execution_plans p "
                        "LEFT JOIN execution_sessions s ON s.plan_id = p.plan_id "
                        "WHERE s.plan_id IS NULL AND p.updated_at < ? "
                        "ORDER BY p.updated_at LIMIT ?)",
                        (cutoff, bounded),
                    ).rowcount
            except sqlite3.DatabaseError as error:
                raise PersistenceIntegrityError("prune transaction failed") from error
        return PruneResult(controller, plans, execution, audit)

    @contextmanager
    def _connect(self, *, create: bool) -> Iterator[sqlite3.Connection]:
        if not create and not self.database.exists():
            raise PersistenceConfigurationError("database is not initialized")
        connection = sqlite3.connect(
            self.database,
            timeout=self.config.busy_timeout_ms / 1_000,
            isolation_level="DEFERRED",
        )
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(f"PRAGMA busy_timeout = {self.config.busy_timeout_ms}")
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _ready_connection(self) -> Iterator[sqlite3.Connection]:
        with self._connect(create=False) as connection:
            version = self._schema_version(connection)
            if version != CURRENT_SCHEMA_VERSION:
                raise PersistenceMigrationError(
                    f"database schema {version} requires migration to {CURRENT_SCHEMA_VERSION}"
                )
            yield connection

    def _execute_write(self, statement: str, parameters: tuple[object, ...]) -> None:
        with self._ready_connection() as connection:
            try:
                with connection:
                    connection.execute(statement, parameters)
            except sqlite3.IntegrityError as error:
                raise PersistenceIntegrityError(
                    "persistent record conflicts with existing data"
                ) from error
            except sqlite3.DatabaseError as error:
                raise PersistenceError("SQLite write failed") from error

    def _get_payload(self, table: str, key: str, value: str) -> str:
        if not value.strip():
            raise PersistenceIntegrityError("record identifier must not be empty")
        allowed = {
            ("controller_sessions", "session_id"),
            ("execution_plans", "plan_id"),
            ("execution_sessions", "execution_id"),
        }
        if (table, key) not in allowed:
            raise PersistenceIntegrityError("invalid repository lookup")
        with self._ready_connection() as connection:
            row = connection.execute(
                f"SELECT payload FROM {table} WHERE {key} = ?", (value,)
            ).fetchone()
        if row is None:
            raise PersistenceNotFoundError(f"unknown persistent record: {value}")
        return str(row[0])

    def _bounded_limit(self, limit: int) -> int:
        if isinstance(limit, bool) or limit < 1 or limit > self.config.max_query_limit:
            raise PersistenceConfigurationError(
                f"limit must be between 1 and {self.config.max_query_limit}"
            )
        return limit

    def _secure_permissions(self) -> None:
        try:
            os.chmod(self.database, 0o600)
        except OSError as error:
            raise PersistenceConfigurationError("cannot secure database permissions") from error

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat()

    @staticmethod
    def _schema_version(connection: sqlite3.Connection) -> int:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        if exists is None:
            return 0
        row = connection.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        ).fetchone()
        return int(row[0])

    @staticmethod
    def _count(connection: sqlite3.Connection, table: str) -> int:
        allowed = {
            "controller_sessions",
            "execution_plans",
            "execution_sessions",
            "adapter_audit_events",
        }
        if table not in allowed:
            raise PersistenceIntegrityError("invalid status table")
        return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    @staticmethod
    def _validate_ordered_sequences(sequences: Iterator[int]) -> None:
        values = tuple(sequences)
        if values and values != tuple(range(1, len(values) + 1)):
            raise PersistenceIntegrityError("event sequences must be contiguous and start at 1")

    @staticmethod
    def _delete_limited(
        connection: sqlite3.Connection,
        table: str,
        timestamp_column: str,
        cutoff: str,
        limit: int,
    ) -> int:
        allowed = {
            ("controller_sessions", "updated_at"),
            ("execution_sessions", "updated_at"),
            ("adapter_audit_events", "timestamp"),
        }
        if (table, timestamp_column) not in allowed:
            raise PersistenceIntegrityError("invalid prune target")
        return connection.execute(
            f"DELETE FROM {table} WHERE rowid IN (SELECT rowid FROM {table} "
            f"WHERE {timestamp_column} < ? ORDER BY {timestamp_column} LIMIT ?)",
            (cutoff, limit),
        ).rowcount
