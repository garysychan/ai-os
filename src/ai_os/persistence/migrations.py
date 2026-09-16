"""Forward-only SQLite schema migrations."""

CURRENT_SCHEMA_VERSION = 1

MIGRATIONS: dict[int, tuple[str, ...]] = {
    1: (
        """
        CREATE TABLE controller_sessions (
            session_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE execution_plans (
            plan_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE execution_sessions (
            execution_id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE adapter_audit_events (
            invocation_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK(sequence > 0),
            task_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            payload TEXT NOT NULL,
            PRIMARY KEY (invocation_id, sequence)
        )
        """,
        "CREATE INDEX controller_sessions_updated ON controller_sessions(updated_at)",
        "CREATE INDEX execution_sessions_updated ON execution_sessions(updated_at)",
        "CREATE INDEX execution_plans_updated ON execution_plans(updated_at)",
        "CREATE INDEX adapter_audit_timestamp ON adapter_audit_events(timestamp)",
    ),
}
