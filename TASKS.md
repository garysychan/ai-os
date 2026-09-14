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
Status: REVIEW  
Dependencies: TASK-0001

Description:
Inspect the GitHub `ai-os` repository and reconcile the actual repository structure with `ARCHITECTURE.md`.

Acceptance Criteria:
- [x] Repository structure inspected.
- [x] Actual modules documented.
- [x] Architecture discrepancies identified.
- [x] Required architecture changes proposed.

Artifacts:
- `docs/repository-architecture-alignment.md`
- `feature/repository-architecture-alignment`

Notes:
- Architecture validation started from authoritative `main` commit `30691a257be5b4d526956b8897e7ea3d06484090`.
- Recursive repository inspection covered 62 Git tree entries.
- Alignment result: WARNING / NON-BLOCKING; no blocking architecture contradiction found.
- Seven discrepancies and prioritized remediation actions are recorded in the alignment report.
- Submitted for Reviewer validation.

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
Dependencies: TASK-0003, TASK-0005

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
Status: DONE  
Dependencies: TASK-0007

Description:
Connect the task state model to the project's durable task tracking mechanism.

Acceptance Criteria:
- [x] Task IDs supported.
- [x] State transitions validated.
- [x] Invalid transitions rejected.
- [x] GitHub integration approach documented.

Artifacts:
- CR-2026-005
- GitHub Issue #7
- `feature/task-schema-state-machine`

Notes:
- A2 human approval received on 2026-09-14.
- Task Schema and State Machine implementation started.
- Runtime Task Schema, State Machine, DONE Gate, and Transition Events implemented.
- CLI commands `aios task validate` and `aios task transitions` implemented.
- GitHub integration remains adapter-based; direct TASKS.md persistence is explicitly deferred.
- Python 3.11 and Python 3.12 passed 41 tests in GitHub Actions Run 34848600031.
- Reviewer validation result: APPROVE.
- PR #8 was marked Ready for Review and squash merged into `main` as commit `93c990a9dbb55b986f6c002681d8622855da7015`.
- Post-merge Control Plane Check Run 34849315810 passed on Python 3.11 and Python 3.12.
- Quality Gate G4 and merge gate G5 passed; task transitioned to `DONE`.

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
Status: DONE  
Dependencies: TASK-0001

Description:
Create a checker that detects contradictions, missing references, invalid states, and undefined agents across Control Plane files.

Acceptance Criteria:
- [x] Required files detected.
- [x] Cross-references checked.
- [x] Agent references checked.
- [x] Workflow states checked.
- [x] Duplicate/structurally provable conflicting rules reported.
- [x] PASS/WARNING/FAIL report generated.

Artifacts:
- CR-2026-003
- `src/ai_os/governance/checker.py`
- `src/ai_os/governance/findings.py`
- `src/ai_os/governance/references.py`
- `src/ai_os/governance/permissions.py`
- `src/ai_os/governance/versions.py`
- GitHub Actions Run 34693342113

Notes:
- CR-2026-003 Fix Cycle completed after Reviewer REQUEST_CHANGES.
- Python 3.11 and Python 3.12 CI passed with 15 tests.
- Deterministic structured contradiction detection is implemented; unrestricted natural-language inference remains outside validation scope.
- Reviewer revalidation result: APPROVE.
- Quality Gate G4 passed; task transitioned to `DONE`.

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

## TASK-0009 — Enforce Main Branch Governance

Priority: P0  
Agent: Controller / Developer  
Status: DONE  
Dependencies: TASK-0007

Description:
Require every change to `main` to use a Pull Request and pass the Python 3.11 and Python 3.12 Control Plane checks.

Acceptance Criteria:
- [x] Every Pull Request triggers both Control Plane checks.
- [x] `Python 3.11` is configured as a required check.
- [x] `Python 3.12` is configured as a required check.
- [x] Direct updates to `main` require a Pull Request.
- [x] Pending or failed required checks block merge.
- [x] Force pushes and deletion of `main` are blocked.
- [x] The `main-governance` ruleset is Active.
- [x] A validation Pull Request confirms enforcement.

Artifacts:
- CR-2026-004
- `.github/workflows/control-plane-check.yml`

Risks:
- A missing required check could leave Pull Requests permanently blocked.
- Repository Ruleset creation requires Owner administration permission.

Notes:
- Implementation started after explicit A3 human approval.
- Repository Owner activated ruleset `main-governance` (Ruleset ID 23053660).
- PR #5 verified required-check blocking and universal Pull Request triggering.
- GitHub Actions Run 34697270854 passed on Python 3.11 and Python 3.12.
- PR #5 was closed without merging its smoke-test artifact.

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
