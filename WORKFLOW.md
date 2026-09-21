# WORKFLOW.md

## 1. Purpose

This document defines the standard execution lifecycle for the AI OS Project.

## 2. Canonical Workflow

```text
REQUIREMENT
    ↓
ANALYSIS
    ↓
PLANNING
    ↓
TASK BREAKDOWN
    ↓
EXECUTION
    ↓
TESTING
    ↓
REVIEW
    ↓
FIX (if required)
    ↓
VALIDATION
    ↓
COMPLETION
```

## 3. State Model

Allowed task states:

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `REVIEW`
- `DONE`

## 4. Stage Definitions

### Stage 0 — Requirement

Responsible: Controller / Planner

Input:
- User request
- Existing Project context

Actions:
- Identify objective.
- Determine scope.
- Identify ambiguity.
- Determine constraints.

Gate:
Requirement is sufficiently understood.

### Stage 1 — Analysis

Responsible: Planner / Researcher

Actions:
- Inspect relevant files/repository.
- Identify dependencies.
- Identify risks.
- Separate facts and assumptions.

Output:
Analysis Summary.

### Stage 2 — Planning

Responsible: Planner

Output:
- Objective
- Approach
- Task list
- Dependencies
- Agents
- Acceptance criteria
- Risks

Gate:
Plan is executable.

### Stage 3 — Task Breakdown

Responsible: Planner

Each task must contain:
- Task ID
- Description
- Priority
- Agent
- Dependencies
- Acceptance Criteria
- Status

Gate:
Tasks are actionable and non-ambiguous.

### Stage 4 — Execution

Responsible: Developer / Researcher / relevant specialist

Rules:
- Inspect context before changing anything.
- Make scoped changes.
- Preserve architecture.
- Record relevant artifacts.

For coding tasks:

```text
Task
 -> Repository inspection
 -> Implementation
 -> Local validation
 -> Test
```

### Stage 5 — Testing

Responsible: Tester / Developer

Actions:
- Run applicable tests.
- Validate acceptance criteria.
- Check regression risks.

Failure:
Move to `BLOCKED` or return to `IN_PROGRESS`, depending on cause.

### Stage 6 — Review

Responsible: Reviewer

Review dimensions:
- Requirements
- Code quality
- Architecture
- Security
- Tests
- Documentation
- Maintainability

Result:

`APPROVE`
or
`REQUEST_CHANGES`
or
`BLOCKED`

### Stage 7 — Fix

Responsible: Fixer / Developer

Actions:
- Address review findings.
- Re-run affected tests.
- Preserve approved scope.

Then return to Review.

### Stage 8 — Validation

Responsible: Reviewer / Controller

Verify:
- Acceptance criteria
- Test results
- Review result
- Documentation/state
- No unresolved blockers

### Stage 9 — Completion

Task may become `DONE` only after required gates pass.

## 5. Human Approval Gates

Human approval is required for:
- Control Plane changes
- Major architecture changes
- Security-sensitive changes
- Destructive operations
- Breaking API changes
- Production-impacting changes
- Ambiguous high-risk decisions

## 6. Change Control Workflow

```text
CHANGE REQUEST
    ↓
IMPACT ANALYSIS
    ↓
CHANGE PROPOSAL
    ↓
REVIEW
    ↓
HUMAN APPROVAL
    ↓
IMPLEMENT
    ↓
CONSISTENCY CHECK
    ↓
VERSION / STATE UPDATE
```

## 7. Error Handling

### Recoverable
Retry or fix locally when:
- Test failure has a clear cause.
- Dependency is temporarily unavailable.
- Implementation defect is isolated.

### Blocking
Set `BLOCKED` when:
- Required information is unavailable.
- Permission is insufficient.
- Architecture conflict exists.
- Required external dependency cannot be obtained.
- Approval is required but unavailable.

## 8. Handoff Protocol

Every handoff must include:

```text
Task ID:
State:
Objective:
Completed:
Artifacts:
Tests:
Risks:
Remaining:
Next Action:
```

## 9. Definition of Done

A task is `DONE` when:
- Acceptance criteria pass.
- Required tests pass.
- Required review passes.
- Required documentation/state is updated.
- No blocking issue remains.

## 10. Default Execution Modes

### QUICK
Minimal analysis and direct execution for low-risk tasks.

### STANDARD
Full planning, implementation, testing, and review.

### DEEP
Expanded research, multi-source validation, deeper architecture/risk analysis, and stronger review.

The selected mode must never bypass mandatory security or approval gates.

## 11. Executable Workflow Packs

The governed Workflow Registry exposes `coding@1`, `trace@1.0.0`, `investment@1.0.0` and
`deep-research@1.0.0`. A pack is selected by exact name and version; no fallback or implicit latest
version is allowed.

TRACE executes its declared `plan -> gather -> synthesize -> review` stages. Investment executes
`scope -> research -> valuation -> risk -> review`. Deep Research executes
`plan -> collect -> triangulate -> analyze -> synthesize -> review`. The final review stage is
mandatory and may complete the Task only with an explicit `APPROVE` result and all State Machine
completion gates satisfied.

Before every dispatch, execution enforces cancellation, timezone-aware deadline and finite step
budgets. Initial authorization enforces Task status, dependency completion, assigned Agents,
canonical permissions and required approval evidence. A pack cannot call Tools or Adapters
directly; any external operation continues through the existing Execution Engine, Tool Registry
and Adapter policies.

Investment and Deep Research declare an output contract that separates `facts`, `inference` and
`assumptions`. TRACE declares `evidence`, `sources` and `conclusions`. Before Reviewer dispatch, the
Workflow Engine verifies that every required section contains non-empty Agent output; missing
sections terminate the session as escalated.

CLI inspection and validation:

```text
aios workflow list
aios workflow describe investment --version 1.0.0
aios workflow validate path/to/definition.json
aios workflow dry-run deep-research TASK-ID --version 1.0.0 --objective "..."
```

Dry-run performs governance and checkpoint creation without Agent dispatch or external side effects.

## 12. Runtime Evidence Lifecycle

Approved runtime boundaries may emit canonical evidence for accepted, started, completed, failed,
cancelled, denied and timed-out outcomes. Events must be redacted before they cross the persistence
boundary and remain append-only after storage. Each trace uses a contiguous sequence beginning at
one; unknown schemas, malformed identifiers, duplicate events and reordered evidence fail closed.

Audit and trace inspection is read-only and query-bounded. It must not change Task status, grant
permissions, satisfy an approval gate, replay a Tool invocation or otherwise become an execution
authority. Every service or CLI query must carry an explicit canonical Agent role authorized for
`read_control`; missing or incompatible query authority fails closed before repository access.

## 13. Runtime Monitoring Lifecycle

Monitoring reads canonical redacted runtime evidence through a bounded repository query, validates
the caller's `read_control` authority, and produces an immutable metric set or health snapshot.
Metrics and health are advisory evidence only: they cannot transition Tasks, dispatch Agents,
approve work or alter an execution result. Invalid labels, excessive windows, stale evidence and
probe failures are surfaced explicitly and never converted into authorization.
