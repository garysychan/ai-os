# ARCHITECTURE.md

## 1. Purpose

This document defines the target architecture for the AI OS + Coding + Codex + GitHub Project.

It is intentionally implementation-oriented while avoiding assumptions that have not been confirmed.

## 2. Architecture Principles

1. Control Plane first.
2. Workflow-driven execution.
3. Explicit agent responsibilities.
4. Human approval for high-impact decisions.
5. GitHub as source control and durable engineering state.
6. Codex as an execution/implementation layer.
7. Modular components and replaceable integrations.
8. Observable, testable, reproducible execution.

## 3. Logical Architecture

```text
User
  |
  v
Project / Controller
  |
  +--> Control Plane
  |      +--> AGENTS.md
  |      +--> PROJECT_RULES.md
  |      +--> ARCHITECTURE.md
  |      +--> WORKFLOW.md
  |
  +--> Planner
  |      |
  |      v
  |    Task Registry / GitHub
  |
  +--> Researcher
  |
  +--> Developer -----> Codex -----> Git Repository
  |
  +--> Tester
  |
  +--> Reviewer
  |
  +--> Fixer
```

## 4. Control Plane

`CONTROL_PLANE.md` governs:
- Governance
- File roles
- Change control
- Permissions
- Versioning
- Consistency

Core documents:
- `AGENTS.md`: agent model
- `PROJECT_RULES.md`: mandatory policy
- `ARCHITECTURE.md`: system design
- `WORKFLOW.md`: execution lifecycle
- `TASKS.md`: current task registry

## 5. Execution Layers

### Layer 0 — Governance
Project Instructions + Control Plane.

### Layer 1 — Planning
Requirement interpretation, decomposition, dependencies, acceptance criteria.

### Layer 2 — Agents
Research, development, testing, review, fixing.

### Layer 3 — Execution
Codex and repository tooling.

### Layer 4 — Source Control
Git/GitHub branches, commits, pull requests, issues where used.

### Layer 5 — Validation
Automated tests, review, acceptance, and human approval.

## 6. GitHub Integration

GitHub is the durable source-control system for the codebase.

Recommended repository structure:

```text
ai-os/
├── README.md
├── AGENTS.md
├── PROJECT_RULES.md
├── ARCHITECTURE.md
├── WORKFLOW.md
├── TASKS.md
├── docs/
├── agents/
├── skills/
├── workflows/
├── scripts/
├── src/
├── tests/
└── .github/
```

The exact structure may evolve through approved architecture changes.

## 7. Codex Integration

Codex is treated as an engineering execution layer.

Typical flow:

```text
Task
  -> Plan
  -> Repository inspection
  -> Implementation
  -> Test
  -> Review
  -> Fix
  -> Commit / PR
```

Codex must operate within repository and Project rules.

## 8. Data / State Model

The minimum execution state is:

```text
Task ID
Objective
Status
Owner Agent
Dependencies
Acceptance Criteria
Artifacts
Tests
Review Result
Risk
```

Recommended lifecycle:

```text
TODO
  -> IN_PROGRESS
  -> REVIEW
  -> DONE

Any active state
  -> BLOCKED
```

## 9. External Integrations

External providers should be isolated behind explicit integration boundaries where practical.

Potential integrations include:
- GitHub
- LLM/model providers
- Web/research sources
- Data APIs
- Databases
- CI/CD systems

Provider-specific behavior must not leak unnecessarily into core business logic.

## 10. Security Architecture

Security boundaries should include:
- Secrets management
- Least-privilege credentials
- Input validation
- External-content isolation
- Repository permission controls
- Review of destructive operations

Secrets must never be stored in the repository or Control Plane files.

## 11. Testing Architecture

Testing should exist at appropriate levels:

```text
Unit
  ↓
Integration
  ↓
Workflow / Agent
  ↓
End-to-End
  ↓
Review / Acceptance
```

Not every task requires every level; risk determines the applicable level.

## 12. Architectural Decision Rule

When an implementation requires a material architectural change:
1. Stop affected implementation.
2. Create an Architecture Change Proposal.
3. Assess impact.
4. Obtain required approval.
5. Update this document.
6. Reconcile workflow and agent implications.
7. Resume execution.

## 13. Executable Workflow Definition Packs

The Workflow Engine registers four built-in, provider-neutral definitions:

- `coding@1`: the compatible Developer, Tester, Reviewer and finite Fixer lifecycle.
- `trace@1.0.0`: plan, evidence gathering, synthesis and independent review.
- `investment@1.0.0`: scope, research, valuation, risk and independent review.
- `deep-research@1.0.0`: plan, collection, triangulation, analysis, synthesis and review.

Workflow packs live under `src/ai_os/workflows/packs/`. Each immutable definition declares its
exact stage order, canonical Agent role, capability, permission, finite dispatch budget and output
contract. The `linear_stage_plan` driver may dispatch only those declared stages and must use the
Controller, Agent Runtime and Task State Machine; it has no direct Tool, Adapter or provider access.

Definition registration and execution are default-deny. Unknown names, versions or drivers;
role/capability/permission mismatches; non-semantic pack versions; invalid stage ordering; and
undeclared Fix Cycles are rejected. Persistent checkpoints carry a SHA-256 identity of the exact
name, version, stage plan, approval requirement, output contract and policy budgets, so incompatible
definitions cannot resume stale execution.

Investment and Deep Research Agent results carry structured output sections. The Workflow Engine
requires non-empty `facts`, `inference` and `assumptions` before the Reviewer may be dispatched;
TRACE similarly requires `evidence`, `sources` and `conclusions`. Missing sections terminate the
Controller session as escalated rather than treating a metadata declaration as completed output.

## 14. Runtime Observability and Audit Trail

`src/ai_os/observability/` defines a provider-neutral evidence boundary over existing Controller,
Execution, Adapter, Tool and Workflow records. It does not authorize work, mutate task state or
replace the owning runtime components.

Every canonical runtime event has a schema version, immutable event identity, strict per-trace
sequence, timezone-aware timestamp, source, lifecycle outcome, Task ID, trace ID and optional
session, Workflow, execution, invocation and Agent correlation. Unknown versions and event values
fail closed. Evidence is redacted before persistence, and the SQLite Runtime Store enforces
append-only identity and ordering constraints.

Runtime event queries are explicitly bounded and may filter only declared indexed fields. Trace
reconstruction is an ordered evidence view, not replay authority. Observability failures must not
silently approve, repeat or alter runtime execution. Service and CLI inspection require an explicit
canonical Agent role with `read_control`; the SQLite repository remains an internal persistence
boundary protected by operating-system file permissions.

## 15. Runtime Metrics and Health Monitoring

`src/ai_os/monitoring/` is a read-oriented operational view over canonical, redacted runtime
events. It derives bounded counters and health snapshots without writing execution state or
becoming an authorization, replay or scheduling path.

Metric names, labels, cardinality and query windows are validated against explicit bounds. Health
uses canonical `HEALTHY`, `DEGRADED`, `FAILED`, `UNAVAILABLE` and `STALE` states. Queries require a
canonical Agent role with `read_control`; arbitrary labels, private diagnostic payloads and
unbounded windows fail closed. Monitoring failures remain isolated from runtime outcomes.
Components publish only canonical health states through narrow injected sinks. Optional probes run
under a bounded timeout; exceptions and timeouts are converted to sanitized `UNAVAILABLE`
evidence. Aggregate metrics include bounded event counts, lifecycle duration, failure rate and
query-capacity utilization derived from the authoritative audit stream.

## 16. Runtime Scheduler and Background Jobs

`src/ai_os/scheduler/` defines versioned, immutable job and dispatch models plus a transactional
SQLite repository over the governed Persistent Runtime Store. Scheduler data contains only Task and
registered Workflow references, bounded timing/retry policy and sanitized state; it never persists
arbitrary callables, shell commands, prompts or provider payloads.

Atomic claims use expiring leases and fencing tokens. A worker receives a `DispatchRequest`, not
execution authority: Controller, Agent, Workflow, Execution, Tool and approval policy must still be
revalidated by the dispatch integration before work can run. Scheduler events append canonical,
redacted Runtime Observability evidence and publish only advisory health signals. Scheduler or
monitoring failure cannot authorize, approve or silently complete execution.


## 17. Runtime Configuration and Secrets Management

`src/ai_os/config/` loads versioned runtime settings through explicit environment profiles and
deterministic precedence. Unknown keys, invalid bounds, profile mismatches and unsafe production
storage fail closed before a typed `RuntimeConfig` can reach a runtime component.

`src/ai_os/secrets/` separates secret references from secret material. Configuration stores only
approved `env://` references; only the Controller with `coordinate` permission may resolve them
through `SecretService`. Secret material has redacted string representations and must never enter
configuration output, logs, runtime events, audit records, task records or repository files.
