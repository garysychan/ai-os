"""Forward-only SQLite schema migrations."""

CURRENT_SCHEMA_VERSION = 3

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
    2: (
        """
        CREATE TABLE runtime_events (
            event_id TEXT PRIMARY KEY,
            trace_id TEXT NOT NULL,
            sequence INTEGER NOT NULL CHECK(sequence > 0),
            task_id TEXT NOT NULL,
            execution_id TEXT,
            invocation_id TEXT,
            event_type TEXT NOT NULL,
            source TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            payload TEXT NOT NULL,
            UNIQUE(trace_id, sequence)
        )
        """,
        "CREATE INDEX runtime_events_trace ON runtime_events(trace_id, sequence)",
        "CREATE INDEX runtime_events_task ON runtime_events(task_id, timestamp)",
        "CREATE INDEX runtime_events_execution ON runtime_events(execution_id, timestamp)",
        "CREATE INDEX runtime_events_invocation ON runtime_events(invocation_id, timestamp)",
        "CREATE INDEX runtime_events_timestamp ON runtime_events(timestamp)",
    ),
    3: (
        """
        CREATE TABLE scheduler_jobs (
            job_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            workflow_name TEXT NOT NULL,
            workflow_version TEXT NOT NULL,
            state TEXT NOT NULL,
            next_run_at TEXT NOT NULL,
            lease_owner TEXT,
            lease_token TEXT,
            lease_expires_at TEXT,
            updated_at TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """,
        "CREATE INDEX scheduler_jobs_due ON scheduler_jobs(state, next_run_at)",
        "CREATE INDEX scheduler_jobs_task ON scheduler_jobs(task_id, updated_at)",
        "CREATE INDEX scheduler_jobs_lease ON scheduler_jobs(lease_expires_at)",
    ),
}
