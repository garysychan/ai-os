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
Status: DONE  
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
- Reviewer validation result: APPROVE.
- PR #11 squash merged into `main` as `22d7b0c4b32e1b2c4a73c4c3e41536c0dc7a0338`.
- Pull Request checks and post-merge Control Plane Check Run 34851475197 passed on Python 3.11 and Python 3.12.
- G4 and G5 passed; TASK-0002 transitioned to `DONE`.

## TASK-0003 — Establish Codex Execution Workflow

Priority: P1  
Agent: Planner / Developer  
Status: DONE  
Dependencies: TASK-0002

Description:
Define the practical workflow for using Codex to implement GitHub repository tasks under AI OS governance.

Acceptance Criteria:
- [x] Task intake defined.
- [x] Repository inspection defined.
- [x] Implementation flow defined.
- [x] Test flow defined.
- [x] Review flow defined.
- [x] Git/PR flow defined.

Artifacts:
- `docs/codex-execution-workflow.md`
- `feature/codex-execution-workflow`

Notes:
- Dependency gate verified: TASK-0002 is DONE.
- Workflow specification started from authoritative `main` commit `79f29ab3c7f0e2d9c3bfb313ef5045be252db590`.
- Operational contract defines intake, repository inspection, planning, implementation, testing, Reviewer/Fix cycle, protected Git/PR flow, completion evidence, handoffs, and stop conditions.
- No authoritative Control Plane semantics or permissions were changed.
- Reviewer validation result: APPROVE.
- PR #13 squash merged into `main` as `8cdf446b2b005bae322240be1d07da8a7e90b217`.
- Pull Request checks and post-merge Control Plane Check Run 34852245761 passed on Python 3.11 and Python 3.12.
- G4 and G5 passed; TASK-0003 transitioned to `DONE`.

## TASK-0004 — Implement Agent Runtime Skeleton

Priority: P1  
Agent: Developer  
Status: DONE  
Dependencies: TASK-0003, TASK-0005

Description:
Create the initial runtime structure for Controller, Planner, Developer, Tester, Reviewer, and Fixer roles.

Acceptance Criteria:
- [x] Agent interfaces defined.
- [x] Agent routing defined.
- [x] Execution state model implemented.
- [x] Basic tests added.

Artifacts:
- CR-2026-006
- GitHub Issue #10
- `feature/agent-runtime`
- `src/ai_os/agents/`
- `tests/agents/`

Notes:
- CR-2026-006 has A2 Human Approval.
- Dependency gate verified: TASK-0003 and TASK-0005 are DONE.
- Agent Runtime implementation started from authoritative `main` commit `d73df382bffea142bc8b51425cfdcf2fc00d4292`.
- Typed Agent contract, seven canonical roles, explicit capabilities/permissions/status contexts, Registry, Router, Runtime, immutable Result/Handoff, and CLI inspection commands implemented.
- Default-deny permissions and task/dependency/status preconditions are enforced without hidden Task mutation.
- Initial CI Run 34854362189 exposed one invalid DONE test fixture; Fix Cycle corrected the fixture and strengthened governed completion evidence handling.
- Pre-review validation passed 68 tests on Python 3.11 and Python 3.12 in Run 34855789460.
- Whole-branch security review added mandatory capability-to-permission mapping and Task role-assignment enforcement.
- Bootstrap and Control Plane Consistency Check passed with only pre-existing non-blocking warnings.
- Reviewer validation result: APPROVE.
- PR #15 was marked Ready for Review and squash merged into `main` as `89d7dd157ac0b7ece7c020ec0b021ec665e12b79`.
- Post-merge Control Plane Check Run 34856360227 passed on Python 3.11 and Python 3.12.
- All acceptance criteria, G4 Reviewer gate, and G5 merge/validation gate passed; TASK-0004 transitioned to `DONE`.

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
Status: REVIEW  
Dependencies: TASK-0004

Description:
Implement automated checks for tests, linting, configuration, and other applicable quality gates.

Acceptance Criteria:
- [x] Test command defined.
- [x] Lint/format checks defined where applicable.
- [x] CI strategy documented.
- [x] Failure behavior defined.

Artifacts:
- `feature/automated-quality-gates`
- Pull Request #18
- `.github/workflows/control-plane-check.yml`
- `docs/quality-gates.md`
- GitHub Actions Run 34914940750

Notes:
- Dependency gate verified: TASK-0004 is DONE.
- CI installs the declared development toolchain and runs compile, Ruff lint, incremental Ruff
  formatting, strict mypy, pytest with the configured 80% branch-coverage threshold, package
  build, bootstrap, and Control Plane consistency gates.
- Python 3.11 and Python 3.12 passed all gates in Run 34914940750.
- Existing Ruff and mypy debt is recorded as narrow file/module-level baseline exceptions;
  new files and non-baselined findings remain blocking.
- TASK-0006 is awaiting independent Reviewer validation and protected merge evidence.

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
