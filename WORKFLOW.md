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