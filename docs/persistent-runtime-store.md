# Persistent Runtime Store

## Scope

TASK-0013 adds an explicit SQLite persistence adapter for Controller sessions, Execution plans and
sessions, and redacted Adapter audit evidence. It does not replace the existing in-memory stores by
default and it does not resume workflows automatically.

## Safety model

- The database path is supplied explicitly and cannot be a Control Plane file, denied path, or
  symbolic link.
- The database file is initialized with owner-only permissions where supported.
- Schema upgrades are forward-only. Unknown newer versions and corrupt records fail closed.
- Runtime records use deterministic JSON codecs; Python pickle is not used.
- Sensitive key/value text is redacted before serialization.
- Controller and Execution event ordering is validated before writes.
- Related Execution plans and sessions can be committed in one transaction.
- Audit events are append-only by `(invocation_id, sequence)`.
- Queries and pruning operations have configured upper bounds.

## CLI

The CLI never selects a database implicitly:

```bash
aios store init --database .ai-os/runtime.sqlite
aios store status --database .ai-os/runtime.sqlite --json
aios store migrate --database .ai-os/runtime.sqlite
aios store session SESSION_ID --database .ai-os/runtime.sqlite --json
aios store execution EXECUTION_ID --database .ai-os/runtime.sqlite --json
aios store audit --database .ai-os/runtime.sqlite --limit 100 --json
```

Inspection commands are read-only. The public Python API exposes bounded pruning, but destructive
retention is deliberately not exposed through the CLI.

## Compatibility and rollback

`InMemorySessionStore` and `InMemoryExecutionStore` remain unchanged. SQLite is opt-in through
`SQLiteRuntimeStore(StoreConfig(...))`. Rollback consists of selecting the in-memory adapters and
retaining or backing up the SQLite file; no Control Plane file is stored in or modified by the
runtime store.
