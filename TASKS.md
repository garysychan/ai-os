# TASKS.md

## AI OS Project Task Registry

This file is the current task/state registry. It is designed to be synchronized with GitHub Issues/Projects where those are used.

## Status Definitions

- `TODO` — planned but not started
- `IN_PROGRESS` — actively being executed
- `BLOCKED` — cannot proceed because of a blocker
- `REVIEW` — implementation is awaiting review/validation
- `DONE` — acceptance criteria and required gates are satisfied

## Priority

- `P0` — critical / blocking
- `P1` — high
- `P2` — normal
- `P3` — enhancement

## Task Template

```text
## TASK-XXXX — Task Name

Priority: P1
Agent: Planner / Developer / Reviewer / etc.
Status: TODO
Dependencies: None

Description:
...

Acceptance Criteria:
- [ ] ...
- [ ] ...

Artifacts:
- ...

Risks:
- ...

Notes:
...
```

## Initial AI OS Tasks

## TASK-0001 — Establish Control Plane

Priority: P0  
Agent: Controller  
Status: DONE  
Dependencies: None

Description:
Establish the five-file Control Plane model and governance rules.

Acceptance Criteria:
- [x] Control documents defined.
- [x] Agent permissions defined.
- [x] Workflow gates defined.
- [x] Change control defined.

## TASK-0002 — Validate Repository Architecture

Priority: P0  
Agent: Planner / Developer  
Status: TODO  
Dependencies: TASK-0001

Description:
Inspect the GitHub `ai-os` repository and reconcile the actual repository structure with `ARCHITECTURE.md`.

Acceptance Criteria:
- [ ] Repository structure inspected.
- [ ] Actual modules documented.
- [ ] Architecture discrepancies identified.
- [ ] Required architecture changes proposed.

## TASK-0003 — Establish Codex Execution Workflow

Priority: P1  
Agent: Planner / Developer  
Status: TODO  
Dependencies: TASK-0002

Description:
Define the practical workflow for using Codex to implement GitHub repository tasks under AI OS governance.

Acceptance Criteria:
- [ ] Task intake defined.
- [ ] Repository inspection defined.
- [ ] Implementation flow defined.
- [ ] Test flow defined.
- [ ] Review flow defined.
- [ ] Git/PR flow defined.

## TASK-0004 — Implement Agent Runtime Skeleton

Priority: P1  
Agent: Developer  
Status: TODO  
Dependencies: TASK-0003

Description:
Create the initial runtime structure for Controller, Planner, Developer, Tester, Reviewer, and Fixer roles.

Acceptance Criteria:
- [ ] Agent interfaces defined.
- [ ] Agent routing defined.
- [ ] Execution state model implemented.
- [ ] Basic tests added.

## TASK-0005 — Implement Task Registry Integration

Priority: P1  
Agent: Developer  
Status: TODO  
Dependencies: TASK-0004

Description:
Connect the task state model to the project's durable task tracking mechanism.

Acceptance Criteria:
- [ ] Task IDs supported.
- [ ] State transitions validated.
- [ ] Invalid transitions rejected.
- [ ] GitHub integration approach documented.

## TASK-0006 — Establish Automated Quality Gates

Priority: P1  
Agent: Tester / Developer  
Status: TODO  
Dependencies: TASK-0004

Description:
Implement automated checks for tests, linting, configuration, and other applicable quality gates.

Acceptance Criteria:
- [ ] Test command defined.
- [ ] Lint/format checks defined where applicable.
- [ ] CI strategy documented.
- [ ] Failure behavior defined.

## TASK-0007 — Control Plane Consistency Checker

Priority: P2  
Agent: Developer  
Status: TODO  
Dependencies: TASK-0001

Description:
Create a checker that detects contradictions, missing references, invalid states, and undefined agents across Control Plane files.

Acceptance Criteria:
- [ ] Required files detected.
- [ ] Cross-references checked.
- [ ] Agent references checked.
- [ ] Workflow states checked.
- [ ] Duplicate/conflicting rules reported.
- [ ] PASS/WARNING/FAIL report generated.

## TASK-0008 — AI OS MVP Validation

Priority: P1  
Agent: Reviewer  
Status: TODO  
Dependencies: TASK-0004, TASK-0005, TASK-0006

Description:
Perform end-to-end validation of the AI OS MVP.

Acceptance Criteria:
- [ ] Requirement-to-task flow validated.
- [ ] Agent handoff validated.
- [ ] Codex execution validated.
- [ ] Testing gate validated.
- [ ] Review gate validated.
- [ ] Failure/escalation path validated.

## Task Change Rules

1. Do not silently delete completed tasks.
2. Preserve Task IDs once issued.
3. Status changes must reflect actual workflow state.
4. Significant scope changes require a new or amended task through Change Control.
5. GitHub Issue/PR identifiers should be recorded when available.

## Current Roadmap

```text
Phase 1 — Governance
  TASK-0001

Phase 2 — Repository Alignment
  TASK-0002

Phase 3 — Codex Execution
  TASK-0003

Phase 4 — Agent Runtime
  TASK-0004

Phase 5 — Task / GitHub Integration
  TASK-0005

Phase 6 — Quality Automation
  TASK-0006

Phase 7 — Control Plane Automation
  TASK-0007

Phase 8 — MVP Validation
  TASK-0008
```
