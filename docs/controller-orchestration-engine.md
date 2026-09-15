# Controller Orchestration Engine

## Runtime contract

The Controller is a deterministic, synchronous coordinator. It validates a Task and its
dependencies, dispatches typed requests only through `AgentRouter` and `AgentRuntime`, delegates
every Task status change to `StateMachine`, and emits immutable ordered trace records.

The executable lifecycle is:

```text
IMPLEMENT -> TEST -> REVIEW -> DONE
               |        |
               v        v
              FIX <-----+
```

Test failures and Reviewer `REQUEST_CHANGES` enter the finite Fix Cycle. Exhausting the configured
limit terminates the session as `ESCALATED`. Reviewer `BLOCKED`, invalid decisions, and specialist
failures are preserved as terminal outcomes; the Controller never converts them into approval.

The core imports no shell, filesystem, network, GitHub, credential, deployment, or model-provider
adapter. Integrations must be supplied through separately authorized adapters.

## Dry-run CLI

Create a validated, side-effect-free session:

```bash
aios run TASK-0010 --objective "Validate Controller lifecycle" --dry-run --json
```

Within the same Python process, inspect the process-local session:

```bash
aios session show <session-id> --json
aios session trace <session-id> --json
```

The initial `InMemorySessionStore` deliberately provides no cross-process persistence. The JSON
returned by `aios run` is therefore the durable handoff for a standalone CLI invocation. A database
or file-backed store is outside CR-2026-007 and requires its own adapter authorization.

## Programmatic lifecycle

`ControllerEngine.run_lifecycle()` executes the full synchronous path. A Task must be
`IN_PROGRESS`, every declared dependency must be `DONE`, and its assigned Agent list must authorize
Developer, Tester, Reviewer, and Fixer when those paths are used. Only the Reviewer Agent's
`ExecutionResult.review_result` controls review routing.

Completion requires all of the existing State Machine gates: acceptance criteria, successful test
evidence, Reviewer `APPROVE`, completed dependencies, no blocking findings, and completion evidence.
The Controller records lifecycle completion evidence, but it never marks acceptance criteria as
complete on behalf of a specialist or Reviewer; validated criteria and their evidence must already
be present on the Task before the transition to `DONE`.
