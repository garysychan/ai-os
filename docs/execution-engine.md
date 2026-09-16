# Execution Engine

## Runtime contract

The Execution Engine is the governed side-effect boundary beneath the Controller. It accepts a
finite typed plan, validates Task state, dependencies, Agent assignment, permission, adapter,
retry and step budgets, and executes steps synchronously in declared order.

The core is provider-neutral and has no shell, filesystem-write, network, GitHub, credential,
model-provider or deployment integration. The initial `NoOpAdapter` is deliberately
side-effect-free. An adapter that declares external side effects is rejected by policy.

The Engine returns immutable results to the Controller. It never changes Task state, completes an
acceptance criterion, produces a Reviewer decision, or bypasses the State Machine.

## Execution lifecycle

```text
CONTROLLER REQUEST
→ VALIDATE TASK / PLAN / AUTHORITY
→ RESOLVE EXPLICIT ADAPTER
→ CHECK PERMISSION / BUDGET
→ EXECUTE STEP
→ RECORD ATTEMPT
→ CONTINUE / RETRY / STOP
→ RETURN IMMUTABLE RESULT
```

Retries are permitted only when the step is explicitly idempotent. Every failed attempt remains in
the ordered trace. Cancellation is checked before each step, and deadline or budget exhaustion
stops execution deterministically.

## CLI dry-run

```bash
aios execution validate plan.json --root . --json
aios execute TASK-0011 --plan plan.json --root . --dry-run --json
aios execution adapters --json
aios execution show <execution-id> --json
aios execution trace <execution-id> --json
```

The CLI constructs only plan-specific no-op adapters. Session inspection is process-local; the JSON
result is the durable handoff for a standalone invocation. Persistent storage and real external
adapters require separate approved changes.

## Plan JSON

```json
{
  "plan_id": "example-plan",
  "task_id": "TASK-0011",
  "max_steps": 1,
  "steps": [
    {
      "step_id": "validate",
      "adapter": "noop",
      "operation": "record",
      "agent_role": "Developer",
      "capability": "implement",
      "required_permission": "modify_code",
      "inputs": {"scope": "dry-run"},
      "idempotent": false,
      "max_retries": 0
    }
  ]
}
```
