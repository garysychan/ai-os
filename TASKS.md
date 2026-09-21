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
Status: DONE  
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
- Reviewer validation result: APPROVE.
- PR #18 was marked Ready for Review and squash merged into `main` as
  `c4d26987a82402fc52bb688d11758ff340b1badf`.
- Post-merge Control Plane Check Run 34915187938 passed on Python 3.11 and Python 3.12.
- G4 and G5 passed; TASK-0006 transitioned to `DONE`.

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
Status: DONE  
Dependencies: TASK-0004, TASK-0005, TASK-0006, TASK-0010, TASK-0011

Description:
Perform end-to-end validation of the AI OS MVP.

Acceptance Criteria:
- [x] Requirement-to-task flow validated.
- [x] Agent handoff validated.
- [x] Codex execution validated.
- [x] Testing gate validated.
- [x] Review gate validated.
- [x] Failure/escalation path validated.

Artifacts:
- `feature/ai-os-mvp-validation`
- `tests/mvp/test_ai_os_mvp.py`
- `docs/ai-os-mvp-validation.md`

Notes:
- Dependency gate verified: TASK-0004, TASK-0005, TASK-0006, TASK-0010 and TASK-0011 are DONE.
- MVP validation started from authoritative `main` commit
  `c3365a6bea80f3b9abfb52971600a860e01a8cc1`.
- Local Tester validation passed 96 tests with 85.72% branch coverage; Ruff, strict mypy,
  package build, bootstrap and Control Plane consistency checks completed.
- Validation covers requirement-to-task schema, Agent handoffs, Controller-to-Execution Engine
  delegation, Tester and Reviewer gates, finite Fixer recovery, blocking and escalation paths.
- GitHub Actions Run 35040213937 passed all gates on Python 3.11 and Python 3.12.
- Whole-branch Reviewer validation result: APPROVE; no blocking finding and no Fix Cycle required.
- TASK-0008 transitioned to `REVIEW` pending protected Pull Request merge evidence.
- PR #27 was squash merged through protected main governance as
  `0e59f2831d81961e6064b0a83c72db31e15b3bdd`; G5 passed.
- Post-merge Control Plane Check Run 35040833006 passed on Python 3.11 and Python 3.12.
- All acceptance criteria and required gates passed; TASK-0008 transitioned to `DONE`.

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

## TASK-0010 — Install Controller Orchestration Engine

Priority: P1  
Agent: Controller / Developer / Tester / Reviewer  
Status: DONE
Dependencies: TASK-0004, TASK-0006

Description:
Install a deterministic, synchronous and provider-neutral Controller that coordinates validated
Tasks through the existing Agent Router, Agent Runtime and State Machine while preserving
Reviewer independence, default-deny permissions and immutable execution evidence.

Acceptance Criteria:
- [x] Canonical immutable Controller Session and event models exist.
- [x] Deterministic Controller Engine coordinates the approved workflow stages.
- [x] All Agent dispatch uses the existing Agent Router and Agent Runtime.
- [x] All Task state changes use the existing State Machine.
- [x] Immutable ordered execution traces, handoffs and evidence are preserved.
- [x] Tester, Reviewer and finite Fix Cycle paths are executable.
- [x] Reviewer independence and default-deny Agent permissions are preserved.
- [x] Blocked, failed, escalated and cancelled terminal outcomes are executable.
- [x] Core orchestration is provider-neutral and performs no uncontrolled side effects.
- [x] Dry-run and session inspection interfaces are available or explicitly deferred by Reviewer.
- [x] Existing public Agent, Task, Workflow and Governance APIs remain compatible.
- [x] Python 3.11 and Python 3.12 quality gates pass.
- [x] Control Plane Consistency Check has no new blocking finding.
- [x] Protected Pull Request governance passes before merge.

Artifacts:
- CR-2026-007
- GitHub Issue #17
- `feature/controller-orchestration-engine`
- `src/ai_os/controller/`
- `tests/controller/`

Risks:
- Controller could bypass specialist Agent or State Machine authority.
- Retry logic could become unbounded or erase original findings.
- Side-effect integration could exceed approved permissions.

Notes:
- CR-2026-007 received A2 Human Approval on 2026-09-15.
- Dependency gate verified: TASK-0004 and TASK-0006 are DONE.
- Implementation must remain deterministic, synchronous, adapter-based and side-effect free.
- Execution started from authoritative `main` commit
  `3575c1be83e5fd41b281e7fb6b649ae8c7333cc9`.
- Immutable Session, Trace, Policy, finite Fix Cycle and terminal outcomes implemented.
- Full Developer, Tester, Reviewer and Fixer lifecycle delegates exclusively through Agent Runtime.
- Task transitions delegate exclusively through State Machine completion gates.
- CLI commands `aios run --dry-run`, `aios session show`, and `aios session trace` implemented
  with an explicit process-local in-memory adapter.
- 82 tests and 85.55% branch coverage passed locally on Python 3.12.
- GitHub Actions Run 34916909604 passed all quality gates on Python 3.11 and Python 3.12.
- Control Plane Consistency Check has only pre-existing non-blocking warnings.
- Fix Cycle corrected mutable-registry CLI test coupling and prevented Controller self-certification of acceptance criteria.
- Final validation passed 83 tests with 85.55% branch coverage; Ruff, mypy and package build passed.
- GitHub Actions Run 34917529582 passed all quality gates on Python 3.11 and Python 3.12.
- Whole-branch Reviewer validation result: APPROVE; G4 passed with no blocking findings.
- PR #21 was squash merged through protected main governance as
  `ea16ecb221773608c112d2368eac0c62419b16aa`; G5 passed.
- All acceptance criteria passed; TASK-0010 transitioned to `DONE`.

## TASK-0011 — Install Execution Engine

Priority: P1
Agent: Controller / Developer / Tester / Reviewer / Fixer
Status: DONE
Dependencies: TASK-0004, TASK-0005, TASK-0006, TASK-0010

Description:
Install a deterministic, synchronous and provider-neutral Execution Engine that executes finite,
typed plans through explicitly registered safe adapters while preserving Agent Runtime, State
Machine, Reviewer and Control Plane authority boundaries.

Acceptance Criteria:
- [x] Canonical immutable Execution Plan, Step, Session, Event and Result models exist.
- [x] Deterministic synchronous Execution Engine exists.
- [x] Typed port and adapter contracts exist.
- [x] Adapter Registry uses explicit, unambiguous and default-deny resolution.
- [x] Capability, permission, task-assignment and budget policies are enforced.
- [x] Step count, retry and cancellation behavior are finite and testable.
- [x] Non-idempotent operations are not retried by default.
- [x] Immutable ordered traces preserve every attempt and outcome.
- [x] Completed, blocked, failed, escalated and cancelled outcomes are executable.
- [x] Results return to Controller without direct Task mutation.
- [x] Reviewer independence and State Machine authority are preserved.
- [x] Core execution remains provider-neutral and side-effect free.
- [x] Only mock, in-memory or no-op adapters are installed initially.
- [x] CLI dry-run, plan validation and inspection are available or explicitly deferred by Reviewer.
- [x] Existing public APIs remain compatible.
- [x] Tests pass on Python 3.11 and Python 3.12.
- [x] Coverage remains at or above the configured 80% threshold.
- [x] Control Plane Consistency Check has no new blocking finding.
- [x] Protected Pull Request governance passes before merge.
- [x] Whole-branch Reviewer result is APPROVE.

Artifacts:
- CR-2026-008
- GitHub Issue #23
- `registry/task-0011-execution-engine`
- Proposed `feature/execution-engine`
- Proposed `src/ai_os/execution/`
- Proposed `tests/execution/`

Risks:
- Execution Engine could become an unrestricted side-effect gateway.
- Adapter resolution could bypass Agent Runtime permissions.
- Retry behavior could repeat destructive or non-idempotent operations.
- Execution logic could duplicate Controller or State Machine authority.
- Unbounded plans or retries could create runaway execution.

Notes:
- CR-2026-008 received A2 Human Approval on 2026-09-15.
- Dependency gate verified: TASK-0004, TASK-0005, TASK-0006 and TASK-0010 are DONE.
- Initial adapters are restricted to mock, in-memory or no-op behavior.
- Production shell, filesystem-write, network, GitHub, credential, model-provider and deployment
  adapters remain outside the approved scope.
- Implementation may start only after this registry change is merged to authoritative `main`.
- Dependency gate verified: all declared dependencies are DONE.
- Adapter Layer Core implementation started from authoritative `main` commit
  `e13cfc369646d56d497046db80cc042809a4ab85`.
- Initial implementation includes typed contracts, versioned Registry, default-deny policy,
  validation, redacted immutable audit evidence, bounded results and read-only File Adapter.
- Local validation passed 102 tests with 85.78% branch coverage; Ruff and strict mypy passed.
- Execution Engine implementation started from authoritative `main` commit
  `6eed49a9d1e7950b74d9dc3a3cfbfa61b5e8b0ab`.
- Tester validation passed 93 tests with 85.72% branch coverage; Ruff, strict mypy and package
  build passed.
- GitHub Actions Run 35037923932 passed all quality gates on Python 3.11 and Python 3.12.
- Reviewer REQUEST_CHANGES identified a capability-to-permission binding gap; Fix Cycle bound
  every step to the canonical mapping and added strict CLI plan-field validation.
- Reviewer revalidation result: APPROVE; no unresolved blocking finding.
- Control Plane Consistency Check has only pre-existing non-blocking warnings.
- TASK-0011 transitioned to `REVIEW` pending protected Pull Request merge evidence.
- PR #25 passed protected main governance and was squash merged as
  `3e7846fcf65649b3fc651af6d3273afa5b4d06e9`; G5 passed.
- All acceptance criteria passed; TASK-0011 transitioned to `DONE`.

## TASK-0012 — Install AI OS V2 Adapter Layer Core

Priority: P1
Agent: Controller / Developer / Tester / Reviewer / Fixer
Status: DONE
Dependencies: TASK-0004, TASK-0005, TASK-0006, TASK-0008, TASK-0010, TASK-0011

Description:
Install the governed Adapter Layer Core between the Execution Engine and external capabilities,
including typed contracts, explicit registration, default-deny policy, validation, redaction,
immutable audit evidence, and the first executable read-only File Adapter.

Acceptance Criteria:
- [x] Canonical immutable Adapter metadata, invocation, result and audit models exist.
- [x] Typed Adapter protocol and explicit Registry exist.
- [x] Unknown Adapter names, versions and operations are denied.
- [x] Capability, permission, Agent assignment and Task-state authority remain enforced.
- [x] Risk, side-effect and idempotency classifications are validated.
- [x] Input/output validation and bounded result handling exist.
- [x] Sensitive values are redacted from audit evidence and errors.
- [x] Cancellation, deadlines and finite retry policy are enforceable.
- [x] Read-only File Adapter enforces approved roots and blocks traversal and symlink escape.
- [x] Read-only File Adapter cannot write, delete, chmod or access denied sensitive files.
- [x] Adapter results cannot directly mutate Task state.
- [x] CLI can list, inspect, validate and dry-run registered Adapters.
- [x] Existing Agent, Controller, Execution, Task, Workflow and Governance APIs remain compatible.
- [x] Python, Web, GitHub and SQLite Adapters are deferred to separately governed Tasks.
- [x] Tests pass on Python 3.11 and Python 3.12.
- [x] Coverage remains at or above the configured 80% threshold.
- [x] Control Plane Consistency Check has no new blocking finding.
- [x] Whole-branch Reviewer result is APPROVE.
- [x] Protected Pull Request governance passes before merge.

Artifacts:
- CR-2026-009
- GitHub Issue #29
- `registry/task-0012-adapter-layer`
- Proposed `feature/adapter-layer`
- Proposed `src/ai_os/adapters/`
- Proposed `tests/adapters/`

Risks:
- Adapter registration could widen Agent permissions or bypass Execution Policy.
- Path resolution could allow traversal, symlink escape or sensitive-file access.
- Audit evidence could leak credentials or sensitive input values.
- Retry or timeout handling could produce unbounded or repeated side effects.

Notes:
- CR-2026-009 received A2 Human Approval on 2026-09-16.
- Dependency gate requires TASK-0004, TASK-0005, TASK-0006, TASK-0008, TASK-0010 and TASK-0011.
- Core contracts and default-deny policy must land before any external Adapter.
- Initial executable scope is restricted to a read-only File Adapter.
- Sandboxed Python, restricted Web, GitHub read-only and SQLite persistence are deferred to
  separately tracked Tasks and must not be silently included in this implementation.
- Implementation may start only after this registry change is merged to authoritative `main`.
- Dependency gate verified: all declared dependencies are DONE.
- Adapter Layer Core implementation started from authoritative `main` commit
  `e13cfc369646d56d497046db80cc042809a4ab85`.
- Typed contracts, versioned Registry, default-deny policy, validation, redacted immutable audit,
  bounded results and read-only File Adapter implemented.
- CLI commands `aios adapter list`, `describe`, `validate`, and `dry-run` implemented.
- Tester validation passed 109 tests with 85.97% branch coverage after Fix Cycle.
- GitHub Actions Run 35094088318 passed all gates on Python 3.11 and Python 3.12.
- Reviewer REQUEST_CHANGES identified retry/cancellation enforcement and result redaction gaps.
- Fix Cycle added finite attempts, non-idempotent retry denial, auditable cancellation, and
  result evidence/error redaction.
- Whole-branch Reviewer revalidation result: APPROVE; no unresolved blocking finding.
- TASK-0012 transitioned to `REVIEW` pending protected Pull Request merge evidence.
- PR #31 was squash merged through protected main governance as
  `6f6ed9bd3d194dd2878dd25f3bb1503ee9862eec`; G5 passed.
- Post-merge Control Plane Check Run 35094796340 passed on Python 3.11 and Python 3.12.
- All acceptance criteria and required gates passed; TASK-0012 transitioned to `DONE`.


## TASK-0013 — Implement SQLite Session and Execution Store

Priority: P1
Agent: Controller / Developer / Tester / Reviewer / Fixer
Status: DONE
Dependencies: TASK-0005, TASK-0006, TASK-0010, TASK-0011, TASK-0012

Description:
Implement a deterministic SQLite-backed Persistent Runtime Store for Controller sessions, Execution
sessions, ordered traces, results and redacted Adapter audit evidence while preserving all existing
Control Plane and runtime authority boundaries.

Acceptance Criteria:
- [ ] Typed persistence contracts and immutable persistence models exist.
- [ ] Versioned SQLite schema and forward-only migration runner exist.
- [ ] Controller sessions and ordered trace/events can be stored and restored.
- [ ] Execution plans, sessions, attempts, events and results can be stored and restored.
- [ ] Redacted Adapter audit evidence can be stored and queried.
- [ ] Transactions prevent partial session writes.
- [ ] Stable ordering and deterministic round-trip serialization are tested.
- [ ] Unknown schema versions and corrupt records fail closed.
- [ ] Database path and file initialization are governed and validated.
- [ ] Secrets and unredacted sensitive values are not persisted.
- [ ] Bounded inspection and retention/pruning interfaces exist.
- [ ] CLI supports init, status, migrate and read-only session inspection.
- [ ] Existing in-memory stores and public APIs remain compatible.
- [x] Tests pass on Python 3.11 and Python 3.12.
- [ ] Coverage remains at or above the configured 80% threshold.
- [ ] Control Plane Consistency Check has no new blocking finding.
- [ ] Whole-branch Reviewer result is APPROVE.
- [ ] Protected Pull Request governance passes before merge.

Artifacts:
- CR-2026-010
- GitHub Issue #33
- `registry/task-0013-persistent-runtime-store`
- Proposed `feature/persistent-runtime-store`
- Proposed `src/ai_os/persistence/`
- Proposed `tests/persistence/`

Risks:
- Persistence could bypass State Machine or Agent authority.
- Partial writes or weak migrations could corrupt runtime evidence.
- Stored traces could leak credentials or other sensitive values.
- SQLite concurrency or locking behavior could cause unsafe retries.
- Database paths could overlap authoritative Control Plane files.

Notes:
- Dependency gate verified: TASK-0005, TASK-0006, TASK-0010, TASK-0011 and TASK-0012 are DONE.
- SQLite must not become the implicit default until implementation and Reviewer validation pass.
- In-memory stores remain the compatibility and rollback path.
- Automatic workflow resumption, distributed storage, arbitrary SQL and background workers are
  outside the approved scope.
- CR-2026-010 received explicit A2 Human Approval on 2026-09-16.
- Implementation may start only after this registry change is merged to authoritative `main`.
- Implementation started from authoritative `main` commit
  `fa2c6e35db5168235f2f808a3456bcaa62ba75d5` on `feature/persistent-runtime-store`.
- SQLite persistence contracts, versioned schema/migrations, deterministic codecs, Controller and
  Execution repositories, redacted Adapter audit storage, bounded pruning and CLI inspection are
  implemented without changing the in-memory defaults.
- Local Tester validation passed 120 tests and 7 subtests with 85.35% branch coverage; Ruff,
  strict mypy, package build and Control Plane Consistency Check passed.
- Whole-branch Reviewer initially requested changes for typed-pair secret redaction, migration file
  permissions, nested symlink traversal and transactional migration rollback coverage.
- Fix Cycle closed all findings and added regression tests for each security/integrity boundary.
- Reviewer revalidation result: APPROVE; no unresolved blocking finding.
- Final local validation passed 121 tests and 7 subtests with 85.56% branch coverage; Ruff,
  strict mypy, package build and Control Plane Consistency Check passed.
- TASK-0013 transitioned to `REVIEW` pending protected Pull Request and Python 3.11/3.12 evidence.
- PR #35 was squash merged through protected main governance as
  `d1a297eff2973f17107b250edba81dd22b74c15b`; G5 passed.
- Post-merge Control Plane Check Run 35103767140 passed on Python 3.11 and Python 3.12.
- All acceptance criteria and required gates passed; TASK-0013 transitioned to `DONE`.

## TASK-0014 — Implement Governed Tool Registry

Priority: P1
Agent: Controller / Developer / Tester / Reviewer / Fixer
Status: DONE
Dependencies: TASK-0004, TASK-0010, TASK-0011, TASK-0012, TASK-0013

Description:
Install a formal, versioned and default-deny Tool Registry above the Adapter Layer. The Registry
is the canonical discovery and policy-binding entry point for AI OS tools while execution remains
delegated to the existing governed Adapter Service.

Acceptance Criteria:
- [x] Immutable Tool metadata, operation, invocation and result models exist.
- [x] Tool names, versions and operations are explicitly registered and uniquely resolved.
- [x] Unknown Tools, versions, operations and duplicate registrations fail closed.
- [x] Every Tool operation binds to an existing versioned Adapter operation.
- [x] Tool and Adapter risk, side-effect and idempotency declarations must agree.
- [x] Capability and required permission use the canonical Agent permission mapping.
- [x] Task state, Agent assignment and explicit approval evidence are enforced where applicable.
- [x] Write-capable Tools remain unauthorized by default.
- [x] Tool execution cannot bypass Adapter Service or Adapter Policy.
- [x] CLI supports `aios tool list`, `describe`, and `validate`.
- [x] Existing Adapter, Execution, Agent and persistence APIs remain compatible.
- [x] Python, Web, Shell, GitHub and other external Tools remain separately governed work.
- [x] Tests pass on Python 3.11 and Python 3.12.
- [x] Coverage remains at or above the configured 80% threshold.
- [x] Control Plane Consistency Check has no new blocking finding.
- [x] Whole-branch Reviewer result is APPROVE.
- [x] Protected Pull Request governance passes before merge.

Artifacts:
- CR-2026-011
- `feature/tool-registry`
- `src/ai_os/tools/`
- `tests/tools/`

Risks:
- Tool resolution could bypass Adapter policy or create a second execution path.
- Tool metadata could understate Adapter risk or side effects.
- Capability-to-permission mismatch could widen Agent authority.
- Tool aliases or versions could become ambiguous.

Notes:
- CR-2026-011 received explicit A2 Human Approval on 2026-09-17.
- Implementation started from authoritative `main` commit
  `48b1ed815ae020a5b6880c0801bb31b050a29933`.
- Initial scope exposes only the existing read-only File Adapter through a governed Tool binding.
- No new external side-effect capability or Agent permission is introduced.
- Local Python 3.12 validation passed 129 tests and 7 subtests with 85.63% branch coverage;
  Ruff, strict mypy and package build passed.
- Control Plane Consistency Check has only pre-existing non-blocking warnings.
- Python 3.11 CI evidence and independent whole-branch Reviewer validation remain pending.
- PR #37 first CI run 35223722529 failed the changed-file format gate on Python 3.11 and 3.12.
- Fix Cycle formatted `tools/policy.py` and `tests/tools/test_policy.py`; the exact CI format
  command and all local quality gates now pass. CI revalidation remains pending.
- CI revalidation Run 35228127530 passed every gate on Python 3.11 and Python 3.12.
- Whole-branch Reviewer requested changes because Tool invocations could not preserve Adapter
  deadlines. Fix Cycle added timezone-aware Tool deadlines, end-to-end Adapter propagation and
  regression coverage for valid, expired and naive deadlines.
- Post-fix GitHub Actions Run 35229499743 passed every quality gate on Python 3.11 and Python 3.12.
- Whole-branch Reviewer revalidation result: APPROVE; no unresolved blocking finding.
- PR #37 passed protected governance and merged as
  `a28fff09c6be87e16d16e587d6ca71c015f666b0`; the repository recorded a merge commit rather than
  the requested squash merge.
- Post-merge main Run 35230315155 passed on Python 3.11 and Python 3.12.
- TASK-0014 transitioned to `REVIEW`; final `DONE` requires this state reconciliation to merge.
- Review-state reconciliation PR #38 merged as
  `7743aed12990cb14628ee310b8dcb564c74a2f93`.
- Post-reconciliation main Run 35234323265 passed on Python 3.11 and Python 3.12.
- All acceptance criteria and required governance gates passed; TASK-0014 transitioned to `DONE`.
- CR-2026-011 is closed as completed.

## TASK-0015 — Implement Governed Workflow Engine

Priority: P1
Agent: Controller / Developer / Tester / Reviewer / Fixer
Status: DONE
Dependencies: TASK-0004, TASK-0005, TASK-0010, TASK-0011, TASK-0013, TASK-0014

Description:
Install a deterministic, versioned and default-deny Workflow Engine that loads, validates,
registers and executes finite workflow definitions while preserving the authority of the Task
State Machine, Controller, Agent Runtime, Execution Engine, Tool Registry and approval gates.

Acceptance Criteria:
- [x] Immutable Workflow definition, stage, session, event and result models exist.
- [x] Workflow names, versions and stages are explicitly registered and uniquely resolved.
- [x] Unknown Workflow names, versions, stages and duplicate registrations fail closed.
- [x] Every executable stage declares one canonical Agent capability and required permission.
- [x] Workflow definitions cannot grant Agent permissions or bypass Task assignment.
- [x] Task status changes occur only through the existing State Machine.
- [x] Agent dispatch occurs only through the existing Controller and Agent Runtime.
- [x] External operations remain governed by Execution, Tool and Adapter policies.
- [x] Finite stage, retry and Fix Cycle budgets are enforced.
- [x] Cancellation and timezone-aware deadlines are enforced.
- [x] Reviewer approval and completion gates cannot be bypassed.
- [x] Immutable ordered session events and results are inspectable.
- [x] In-memory persistence remains the default with an explicit persistent-store boundary.
- [x] Resume rejects corrupt, terminal or definition-version-mismatched checkpoints.
- [x] A built-in Coding lifecycle is registered without hard-coding provider behavior.
- [x] TRACE, Investment and Deep Research definitions remain separately governed extensions.
- [x] CLI supports workflow list, describe, validate, dry-run and session inspection.
- [x] Existing State Machine, Controller, Execution, Tool and persistence APIs remain compatible.
- [x] Tests pass on Python 3.11 and Python 3.12.
- [x] Coverage remains at or above the configured 80% threshold.
- [x] Control Plane Consistency Check has no new blocking finding.
- [x] Whole-branch Reviewer result is APPROVE.
- [x] Protected Pull Request governance passes before merge.

Artifacts:
- CR-2026-012
- `feature/workflow-engine`
- `src/ai_os/workflows/`
- `tests/workflows/`

Risks:
- Workflow orchestration could duplicate or bypass Controller and State Machine authority.
- Declarative stages could widen Agent permissions through unvalidated metadata.
- Resume could accept stale or corrupt definition versions.
- Unbounded stages or Fix Cycles could create runaway execution.
- Workflow code could become an unrestricted external side-effect gateway.

Notes:
- CR-2026-012 received explicit A2 Human Approval on 2026-09-18.
- Dependency gate verified: TASK-0004, TASK-0005, TASK-0010, TASK-0011, TASK-0013 and
  TASK-0014 are DONE.
- Implementation started from authoritative `main` commit
  `e25eda1e1d2bcddfd466303863ff5c9238116981`.
- Initial scope is the Workflow Engine Core and a governed Coding lifecycle; provider-specific,
  distributed and background execution remain outside the approved scope.
- Workflow Engine Core, governed Coding lifecycle and CLI integration were implemented under
  `src/ai_os/workflows/`, `tests/workflows/` and `tests/test_workflow_cli.py`.
- Local Tester Validation passed 144 tests and 7 subtests with 86% branch coverage on Python 3.12;
  Ruff, mypy, package build and all targeted Workflow tests passed.
- Control Plane Consistency Check completed with `WARNING` and no blocking finding; all reported
  warnings pre-date this Task and remain subject to approved Control Plane change control.
- GitHub Python 3.11 and Python 3.12 Checks passed before whole-branch review.
- Whole-branch Reviewer requested changes for definition/dispatch alignment, pre-dispatch budget
  enforcement and cross-process CLI session inspection.
- Reviewer Fix Cycle made `controller_lifecycle` definitions fail closed unless their stages match
  the canonical lifecycle, added per-dispatch budget/deadline/cancellation guards with terminal
  audit events, and added a JSON-backed Workflow session store for cross-process CLI inspection.
- Fix Cycle validation passed 146 tests and 7 subtests with 85.41% branch coverage on both Python
  3.11 and Python 3.12; Ruff, mypy, package build and Control Plane checks passed.
- Whole-branch Reviewer revalidation at commit `eaa055c` returned `APPROVE`; RV-001, RV-002 and
  RV-003 are closed with no new blocking finding.
- TASK-0015 transitioned from `IN_PROGRESS` to `REVIEW` and is Ready for Review.
- PR #41 passed protected Pull Request governance and was squash merged to `main` as
  `a802ea5b89d79595fc6f10d1e5c63b53c91e0fb4`.
- Post-merge Control Plane Check Run 35329612269 (Run #141) completed successfully on `main`
  commit `a802ea5` with Python 3.11 and Python 3.12 passing.
- All acceptance criteria and governance gates passed; TASK-0015 transitioned from `REVIEW` to
  `DONE` and CR-2026-012 is closed as completed.

## TASK-0016 — Install Workflow Definition Packs

Priority: P1
Agent: Controller / Planner / Researcher / Developer / Tester / Reviewer / Fixer
Status: DONE
Dependencies: TASK-0004, TASK-0005, TASK-0010, TASK-0011, TASK-0012, TASK-0013, TASK-0014, TASK-0015

Description:
Install governed, versioned Workflow Definition Packs for TRACE, Investment and Deep Research on
top of the approved Workflow Engine Core without widening Agent permissions, bypassing Controller
authority or embedding provider-specific behavior.

Acceptance Criteria:
- [x] TRACE, Investment and Deep Research definitions have explicit names and semantic versions.
- [x] Every declared stage maps to one canonical Agent role, capability and required permission.
- [x] Workflow-specific drivers execute only stages declared by the selected definition.
- [x] Unknown drivers, stages, versions and invalid stage ordering fail closed.
- [x] Workflow packs cannot grant permissions or bypass Task assignment and dependency gates.
- [x] External data, Tool and Adapter operations remain governed by their existing policies.
- [x] Stage, retry, deadline, cancellation and approval budgets are enforced before dispatch.
- [x] Investment and Deep Research outputs distinguish facts, inference and assumptions.
- [x] Checkpoints bind to the exact Workflow name, version, stage plan and policy budget.
- [x] CLI supports listing, describing, validating and dry-running each Workflow pack.
- [x] Coding Workflow and existing public APIs remain backward compatible.
- [x] Authoritative architecture and workflow documents reflect implemented behavior.
- [x] Positive, negative, permission, budget, checkpoint and cross-process tests exist.
- [x] Tests pass on Python 3.11 and Python 3.12.
- [x] Coverage remains at or above the configured 80% threshold.
- [x] Control Plane Consistency Check has no new blocking finding.
- [x] Whole-branch Reviewer result is APPROVE.
- [x] Protected Pull Request governance passes before merge.

Artifacts:
- CR-2026-013
- `feature/workflow-definition-packs`
- `src/ai_os/workflows/packs/`
- `tests/workflows/packs/`

Risks:
- Declarative definitions could become an indirect permission-escalation path.
- Research workflows could dispatch undeclared stages or ungoverned external operations.
- Domain-specific stage semantics could weaken the Controller and Task State Machine boundaries.
- Stale checkpoints could resume against incompatible Workflow pack versions.
- Unbounded research or retry loops could create runaway execution and cost.

Notes:
- Change ID: CR-2026-013.
- Requester: Repository Owner.
- Date: 2026-09-18.
- Target Document: `ARCHITECTURE.md`, `WORKFLOW.md`, `TASKS.md` and executable Workflow modules.
- Change Type: WORKFLOW / ARCHITECTURE.
- Classification: MINOR compatible capability extension with security-sensitive execution impact.
- Reason: Install the governed TRACE, Investment and Deep Research extensions reserved by
  TASK-0015.
- Current State: `coding@1` is the only registered executable Workflow definition.
- Proposed Change: Add three versioned definition packs and the minimum explicit driver boundary
  required to execute only their declared stages.
- Affected Documents: `ARCHITECTURE.md`, `WORKFLOW.md`, `TASKS.md`.
- Affected Agents: Controller, Planner, Researcher, Developer, Tester, Reviewer and Fixer.
- Impact: Adds domain workflows while preserving existing authority and public APIs.
- Dependencies: TASK-0004, TASK-0005, TASK-0010 through TASK-0015 as listed above.
- Approval Required: Explicit A2 Human Approval before implementation.
- Approval Evidence: Repository Owner issued `APPROVE CR-2026-013` on 2026-09-18.
- CR Status: APPROVED / IMPLEMENTATION AUTHORIZED.
- Implementation started from authoritative `main` commit
  `ef28bdc` on `feature/workflow-definition-packs`; TASK-0016 transitioned to `IN_PROGRESS`.
- TRACE, Investment and Deep Research packs, the fail-closed linear stage driver, exact checkpoint
  fingerprinting, CLI integration and authoritative documentation are installed.
- Local Tester pre-validation passed 156 tests and 7 subtests with 85.57% branch coverage; Ruff,
  formatting, mypy, package build and cross-process Workflow Pack dry-run passed.
- Control Plane Consistency Check completed with `WARNING` and no new blocking finding; reported
  warnings pre-date TASK-0016 and remain governed separately.
- Initial whole-branch Reviewer validation returned `REQUEST_CHANGES`: the Reviewer dispatch guard
  was not adjacent to dispatch, Pack stage names/order were not canonicalized, and domain output
  sections were declared but not validated against actual Agent results.
- Reviewer Fix Cycle moved the deadline/cancellation/step guard immediately before every dispatch,
  default-denied unknown or reordered Pack stages, and added structured non-empty output validation
  before Reviewer dispatch.
- Post-fix local validation passed 160 tests and 7 subtests with 85.63% branch coverage; Ruff,
  formatting and mypy passed. Control Plane status remains `WARNING` with no new blocker.
- Post-fix GitHub Actions Control Plane Check Run #148 passed on commit `06aa081` for Python 3.11
  and Python 3.12.
- Whole-branch Reviewer revalidation result: `APPROVE`; all original findings are resolved and
  TASK-0016 transitioned from `IN_PROGRESS` to `REVIEW`, ready for Pull Request review.
- PR #44 Run 35487670252 failed on Python 3.11 and Python 3.12 because the cross-process dry-run
  test reused authoritative TASK-0016 after its status became `REVIEW`; TASK-0016 returned to
  `IN_PROGRESS` for a test-isolation Fix Cycle.
- Test-isolation Fix Cycle replaced the mutable authoritative Task dependency with an independent
  `TASK-9998` fixture; local validation passed and PR #44 Run 35494291603 passed on commit
  `560f4da` for Python 3.11 and Python 3.12.
- Final whole-branch Reviewer revalidation result: `APPROVE`; no unresolved blocking finding.
  TASK-0016 transitioned from `IN_PROGRESS` to `REVIEW` pending protected merge governance.
- PR #44 passed protected governance and was squash-merged to `main` as
  `e4e6138150cd601bd4e4baac42d73d12dedf5eeb`.
- Post-merge main Control Plane Check Run 35494646575 passed on Python 3.11 and Python 3.12.
- All acceptance criteria and required governance gates passed; TASK-0016 transitioned from
  `REVIEW` to `DONE` and CR-2026-013 is closed as completed.
- CR Final Status: CLOSED / COMPLETED.

## TASK-0017 — Install Runtime Observability and Audit Trail

Priority: P1
Agent: Controller / Planner / Developer / Tester / Reviewer / Fixer
Status: DONE
Dependencies: TASK-0005, TASK-0006, TASK-0010, TASK-0011, TASK-0012, TASK-0013, TASK-0014, TASK-0015, TASK-0016

Description:
Install a unified, governed Runtime Observability and Audit Trail over the existing Controller,
Execution, Adapter, Tool, persistence and Workflow evidence without creating a second execution
authority or exposing secrets.

Acceptance Criteria:
- [x] A canonical immutable runtime event envelope identifies event, timestamp, task, session,
  workflow, execution, Agent and correlation context where applicable.
- [x] Existing Controller, Execution, Adapter, Tool and Workflow evidence is normalized through
  explicit integration boundaries without duplicating their decision authority.
- [x] Lifecycle events cover accepted, started, completed, failed, cancelled, denied and timed-out
  outcomes where applicable.
- [x] Permission and approval decisions are traceable without recording credentials or sensitive
  payloads.
- [x] Redaction is fail-closed, deterministic and applied before persistence or presentation.
- [x] Audit records are append-only and reject invalid ordering, malformed identifiers and
  integrity violations.
- [x] SQLite persistence supports atomic event append, bounded queries, retention and reopen
  recovery through the existing Persistent Runtime Store boundary.
- [x] Correlation preserves `task_id`, `session_id`, `workflow_session_id`, `execution_id`,
  `invocation_id` and `trace_id` relationships when those identifiers exist.
- [x] CLI supports bounded audit listing, filtered event inspection and trace reconstruction in
  human-readable and JSON formats.
- [x] Unknown event types, unsupported schema versions and unauthorized queries fail closed.
- [x] Observability failure cannot silently authorize, replay or alter an execution outcome.
- [x] Existing public APIs remain backward compatible unless a separately approved change states
  otherwise.
- [x] Positive, negative, redaction, permission, ordering, corruption, persistence and
  cross-process tests exist.
- [x] Tests pass on Python 3.11 and Python 3.12.
- [x] Coverage remains at or above the configured 80% threshold.
- [x] Control Plane Consistency Check has no new blocking finding.
- [x] Whole-branch Reviewer result is APPROVE.
- [x] Protected Pull Request governance passes before merge.

Proposed Artifacts:
- CR-2026-014
- `feature/runtime-observability-audit`
- `src/ai_os/observability/`
- `tests/observability/`
- CLI integration and Persistent Runtime Store migrations required by the approved design

Risks:
- A parallel audit model could diverge from existing Controller, Execution and Adapter evidence.
- Sensitive prompts, credentials, filesystem paths or provider payloads could leak through events.
- Incomplete correlation could produce misleading or unverifiable execution histories.
- Audit writes could change execution outcomes or leave partial evidence after a transaction fails.
- Unbounded event retention or queries could create storage and performance exhaustion.
- Mutable or reorderable records could invalidate governance evidence.

Notes:
- Change ID: CR-2026-014.
- Requester: Repository Owner.
- Date: 2026-09-20.
- Target Document: `ARCHITECTURE.md`, `WORKFLOW.md`, `TASKS.md` and executable runtime modules.
- Change Type: ARCHITECTURE / WORKFLOW / SECURITY.
- Classification: MINOR compatible capability extension with security-sensitive audit impact.
- Reason: Provide one inspectable and durable execution history across the installed AI OS V2
  runtime layers.
- Current State: Controller and Execution traces, Adapter audit events, Workflow events and SQLite
  persistence exist, but no canonical cross-runtime event envelope, correlation model or unified
  inspection surface exists.
- Proposed Change: Add a governed observability boundary that normalizes existing evidence,
  persists redacted append-only events and reconstructs bounded traces without owning execution
  decisions.
- Affected Documents: `ARCHITECTURE.md`, `WORKFLOW.md`, `TASKS.md`.
- Affected Agents: Controller, Planner, Developer, Tester, Reviewer and Fixer.
- Impact: Adds runtime traceability and audit inspection while preserving existing authority,
  permission and execution boundaries.
- Dependencies: TASK-0005, TASK-0006 and TASK-0010 through TASK-0016 as listed above.
- Approval Required: Explicit A2 Human Approval before implementation.
- Approval Evidence: Repository Owner issued `APPROVE CR-2026-014` on 2026-09-20.
- CR Status: APPROVED / IMPLEMENTATION AUTHORIZED.
- Implementation was authorized to begin on the approved feature branch.
- Implementation started from authoritative `main` commit `570b20b` on
  `feature/runtime-observability-audit`; TASK-0017 transitioned to `IN_PROGRESS`.
- Runtime Observability Core, explicit evidence normalizers, SQLite schema v2 persistence and
  `audit`/`trace` CLI inspection are installed without adding execution authority.
- Local Python 3.12 validation passed 189 tests and 7 subtests with 85.12% branch coverage; Ruff,
  strict mypy and package build passed.
- Control Plane Consistency Check completed with `WARNING` and no new blocking finding; all
  reported warnings pre-date TASK-0017 and remain governed separately.
- Python 3.11 CI, independent Whole-branch Reviewer validation and protected Pull Request
  governance remain pending.
- Initial Whole-branch Reviewer validation returned `REQUEST_CHANGES`: opaque credential and
  provider payloads could leak, runtime sinks and Tool evidence were incomplete, terminal outcomes
  could be misclassified, cross-source sequences collided, trace ordering used timestamps,
  identifiers were under-validated and human CLI output lacked inspectable evidence.
- Reviewer Fix Cycle changed sensitive opaque text to fail-closed whole-field redaction; added
  dependency-injected Controller, Execution, Adapter, Tool and Workflow evidence sinks; mapped
  denied, failed, cancelled and timed-out outcomes explicitly; added atomic global trace sequence
  allocation and sequence-ordered reconstruction; enforced bounded identifier grammars; and
  rendered sanitized human-readable event details.
- Post-fix local validation passed 189 tests and 7 subtests with 85.12% branch coverage; Ruff,
  strict mypy, package build, Task Schema and Control Plane checks passed with no new blocker.
- Whole-branch Reviewer revalidation remained `REQUEST_CHANGES`: arbitrary opaque evidence is not
  default-redacted, same-trace concurrent sequence allocation is not serialized, and
  pre-execution denial evidence is incomplete outside the Adapter boundary. The affected
  acceptance criteria were reopened and TASK-0017 remains `IN_PROGRESS`.
- Reviewer Fix Cycle Round 2 default-redacts all opaque summary/evidence and preserves only
  allowlisted identifier-like correlation values; serializes sequence allocation with
  `BEGIN IMMEDIATE` and validates 32 concurrent same-trace writers; and records pre-execution
  Controller, Execution, Tool and Workflow authorization denials through failure-isolated sinks.
- Round 2 local validation passed 195 tests and 7 subtests with 84.98% branch coverage; Ruff,
  strict mypy, package build, Task Schema and Control Plane checks passed with no new blocker.
- Final Reviewer revalidation after Round 2 remained `REQUEST_CHANGES`: correlation values used a
  generic permissive grammar, Controller dispatch policy denials bypassed the denial sink, and
  service/CLI audit reads lacked an explicit query authorization context.
- Reviewer Fix Cycle Round 3 preserves only key-specific numeric sequence and canonical stage
  correlation values; records Controller dispatch denials; and requires an authorized canonical
  Agent role with `read_control` before service or CLI repository access.
- Round 3 regression validation passed 197 tests and 7 subtests; Task Schema, Python compile and
  Control Plane checks passed with no new blocker. The prior shared validation environment lost its
  Python executable, so Ruff and strict mypy revalidation must be confirmed by GitHub CI.
- Final Reviewer Round 3 kept one blocker open: uppercase private data could pass the stage format
  check and `agent_role` accepted arbitrary strings.
- Reviewer Fix Cycle Round 4 replaced the stage format check with canonical Controller/Workflow
  stage allowlists and rejects non-canonical Agent roles before persistence or presentation.
- Round 4 regression validation passed 199 tests and 7 subtests; Python compile and diff checks
  passed. Ruff and strict mypy remain delegated to the required GitHub Python 3.11/3.12 checks.
- Whole-branch Final Reviewer Revalidation Round 4 returned `APPROVE` for implementation commit
  `4032e815c924d18ff4794c79af2f09b4efc7b326`; no unresolved security or consistency blocker
  remains. Required GitHub Python 3.11/3.12 and protected Pull Request gates remain pending.
- The first post-review Python 3.11/3.12 run failed only Ruff E501 because one validation line was
  101 characters against the 100-character limit. The CI Fix Cycle split that statement without
  changing runtime behavior; fresh Python 3.11/3.12 checks remain required.
- The next Python 3.11/3.12 run passed Ruff lint but failed `ruff format --check` on one CLI call.
  CI Fix Cycle Round 2 applied the formatter's exact one-line output without changing behavior;
  fresh Python 3.11/3.12 checks remain required.
- The post-fix GitHub matrix completed successfully on Python 3.11 and Python 3.12 for commit
  `b2c47641ba994f63e7297ad38b490109b39eb8f6`. With Final Reviewer `APPROVE` and no open
  implementation blocker, TASK-0017 transitioned from `IN_PROGRESS` to `REVIEW` and is Ready for
  Review. Protected Pull Request governance remains required before merge.
- PR #47 was squash merged through protected main governance as
  `fd5f5b9435362329aa080f5c35c7ebf10f5143ae`.
- Post-merge Main Run `35516129407` passed the required Python 3.11 and Python 3.12 checks.
- All acceptance criteria and governance gates passed; TASK-0017 transitioned from `REVIEW` to
  `DONE` and CR-2026-014 is `CLOSED / COMPLETED`.

## TASK-0018 — Install Runtime Metrics and Health Monitoring

Priority: P1
Agent: Controller / Planner / Developer / Tester / Reviewer / Fixer
Status: DONE
Dependencies: TASK-0010, TASK-0011, TASK-0013, TASK-0014, TASK-0015, TASK-0016, TASK-0017

Description:
Install a governed Runtime Metrics and Health Monitoring layer over the authoritative runtime
evidence. The layer reports bounded operational health and aggregate metrics without acquiring
execution authority, exposing sensitive payloads or replacing the Runtime Observability audit
trail.

Acceptance Criteria:
- [x] Canonical immutable metric, health-check and health-snapshot models are versioned.
- [x] Health states are explicit, deterministic and limited to documented canonical values.
- [x] Controller, Execution, Adapter, Tool, Workflow, persistence and observability components can
  publish health signals through explicit dependency-injected boundaries.
- [x] Metrics are derived from authoritative runtime events or explicit probes without mutating
  execution state.
- [x] Counters, durations, failure rates and capacity indicators use bounded names, labels,
  cardinality and query windows.
- [x] Secrets, prompts, filesystem paths, provider payloads and arbitrary private values cannot be
  used as metric labels or health details.
- [x] Stale, unavailable, degraded and failed components are distinguishable without treating
  monitoring failure as execution authorization.
- [x] Probe timeouts and failures are isolated and cannot block or change an execution outcome.
- [x] Metric and health persistence, if installed, uses the governed Persistent Runtime Store with
  bounded retention and forward-only migration.
- [x] Query access requires canonical Agent identity and the existing `read_control` permission.
- [x] CLI supports bounded `aios health` and `aios metrics` inspection in human-readable and JSON
  formats.
- [x] Unknown metric types, invalid health states, unbounded labels and unauthorized queries fail
  closed.
- [x] Existing Runtime Observability, Controller and Execution public APIs remain compatible.
- [x] Positive, negative, authorization, timeout, redaction, persistence and recovery tests exist.
- [x] Tests pass on Python 3.11 and Python 3.12.
- [x] Coverage remains at or above the configured 80% threshold.
- [x] Control Plane Consistency Check has no new blocking finding.
- [x] Whole-branch Reviewer result is APPROVE.
- [x] Protected Pull Request governance passes before merge.

Proposed Artifacts:
- CR-2026-015
- Proposed `feature/runtime-metrics-health`
- Proposed `src/ai_os/monitoring/`
- Proposed `tests/monitoring/`
- Proposed CLI integration for `aios health` and `aios metrics`
- Persistent Runtime Store migration only if required by the approved design

Risks:
- High-cardinality labels could exhaust memory or storage.
- Health probes could accidentally become a second execution or authorization path.
- Sensitive runtime data could leak through metric dimensions or diagnostic messages.
- Monitoring failures could incorrectly report healthy state or block normal execution.
- Unbounded retention or query windows could create resource exhaustion.
- Aggregated metrics could diverge from the authoritative append-only audit trail.

Notes:
- Change ID: CR-2026-015.
- Requester: Repository Owner.
- Date: 2026-09-21.
- Target Document: `ARCHITECTURE.md`, `WORKFLOW.md`, `TASKS.md` and executable runtime modules.
- Change Type: ARCHITECTURE / WORKFLOW / SECURITY.
- Classification: MINOR compatible capability extension with operational and privacy impact.
- Reason: Add an operational view of runtime availability, degradation, failures, latency and
  bounded aggregate activity above the installed Runtime Observability and Audit Trail.
- Current State: Runtime events are normalized, redacted, persisted and queryable, but the runtime
  has no canonical health model, governed probes or bounded metric aggregation surface.
- Proposed Change: Add a read-oriented monitoring boundary that derives aggregate metrics from
  authoritative evidence and accepts explicit health signals without owning execution decisions.
- Affected Documents: `ARCHITECTURE.md`, `WORKFLOW.md`, `TASKS.md`.
- Affected Agents: Controller, Planner, Developer, Tester, Reviewer and Fixer.
- Impact: Adds runtime diagnosis and operational visibility while preserving Agent authority,
  permission, audit and execution boundaries.
- Dependencies: TASK-0010, TASK-0011 and TASK-0013 through TASK-0017 as listed above.
- Approval Required: Explicit A2 Human Approval before implementation.
- Approval Evidence: Repository Owner issued `APPROVE CR-2026-015` on 2026-09-21.
- CR Status: APPROVED / IMPLEMENTATION AUTHORIZED.
- Implementation may begin on a dedicated feature branch after this approval record is merged to
  authoritative `main`; TASK-0018 remains `TODO` until that branch is created.
- Implementation started on `feature/runtime-metrics-health`; TASK-0018 transitioned from `TODO`
  to `IN_PROGRESS`.
- Runtime Metrics and Health Monitoring Core now derives bounded metrics and canonical health from
  redacted runtime events, enforces `read_control`, and exposes `aios health` / `aios metrics`
  without adding persistence or execution authority.
- Initial local validation passed 208 tests and 7 subtests; Python compile, Task Schema and Control
  Plane checks passed with no new blocker. GitHub Python 3.11/3.12 and Reviewer gates remain open.
- Component signal sinks, isolated bounded probes, lifecycle duration, failure-rate and query
  capacity metrics are installed. Probe exceptions and timeouts produce sanitized unavailable
  evidence without changing execution outcomes.
- Expanded local Tester validation passed 213 tests and 7 subtests; Python compile and changed-file
  line bounds passed. GitHub Python 3.11/3.12 and Whole-branch Reviewer gates remain open.
- Initial Whole-branch Reviewer validation returned `REQUEST_CHANGES`: models were not versioned or
  fully canonical, metric identifiers/units/labels were too permissive, future events entered
  windows, thread-based probe timeouts could keep a process alive, human CLI output was JSON, and
  component integration plus monitoring recovery evidence were incomplete.
- Reviewer Fix Cycle added schema versions and enum-backed models; exact metric/unit/label
  allowlists and finite/cardinality checks; future-event exclusion; terminable process-isolated
  probes; distinct human CLI rendering; dependency-injected sinks for every installed runtime
  boundary; and SQLite reopen/recovery coverage over the authoritative audit store.
- Reviewer Revalidation kept three blockers open: metric names were not bound to canonical units
  and value ranges, health model annotations did not validate construction, and a probe ignoring
  SIGTERM could block an unbounded `join()`.
- Reviewer Fix Cycle Round 2 enforces exact name/unit/value contracts, validates health schemas and
  nested canonical types during construction, and uses bounded terminate/kill/join cleanup with a
  regression probe that ignores SIGTERM.
- Whole-branch Reviewer Revalidation Round 2 returned `APPROVE` at
  `71b75650cd8e7fac73999887639bcdbc77cc217b`; independent validation passed 225 tests and 7
  subtests with no unresolved security, authority or compatibility blocker. GitHub Python
  3.11/3.12 and protected Pull Request gates remain open.
- CI Fix Cycles corrected changed-file Ruff formatting and strict Mypy annotations without
  changing runtime behavior. GitHub Python 3.11 and Python 3.12 checks passed on remote commit
  `be18470`; local revalidation passed 225 tests and 7 subtests with 84.71% branch coverage.
- Final Whole-branch Reviewer Validation returned `APPROVE` for remote commit `be18470`; no
  blocking security, authority, compatibility or consistency finding remains. TASK-0018
  transitioned from `IN_PROGRESS` to `REVIEW` and is Ready for Review. Protected Pull Request
  governance remains required before merge.
- PR #51 passed protected governance and was squash merged to `main` as
  `d2c7ecd0ae8dd7c48406a03e7fa2d0f557f8abcd`.
- Post-merge Main Control Plane Check Run `35586188019` passed the required Python 3.11 and
  Python 3.12 checks on the squash commit.
- Independent metric and health persistence was not installed; monitoring continues to read the
  governed Persistent Runtime Store's authoritative audit events, so no new retention or migration
  boundary was introduced.
- All acceptance criteria and required governance gates passed; TASK-0018 transitioned from
  `REVIEW` to `DONE` and CR-2026-015 is `CLOSED / COMPLETED`.
- CR Final Status: CLOSED / COMPLETED.

## TASK-0019 — Install Runtime Scheduler and Background Jobs

Priority: P1
Agent: Controller / Planner / Developer / Tester / Reviewer / Fixer
Status: TODO
Dependencies: TASK-0005, TASK-0006, TASK-0010, TASK-0011, TASK-0013, TASK-0014,
TASK-0015, TASK-0017, TASK-0018

Description:
Install a governed Runtime Scheduler and Background Jobs layer that can persist, claim, execute,
retry, cancel and inspect bounded jobs without bypassing Task dependencies, Controller authority,
Agent permissions, Workflow budgets, Tool policy, approval gates or the Execution Engine.

Acceptance Criteria:
- [ ] Canonical immutable schedule, job, attempt, lease and result models are explicitly versioned.
- [ ] One-time, delayed and bounded recurring schedules use timezone-aware timestamps and a
  deterministic clock boundary.
- [ ] Background jobs reference approved Tasks and registered Workflow definitions; arbitrary
  callables, shell commands and provider payloads are not persisted or executed.
- [ ] The Scheduler dispatches work only through the existing Controller, Agent Runtime, Workflow
  Engine and Execution Engine authority chain.
- [ ] Task dependency, assignment, permission and approval gates are revalidated immediately
  before every dispatch.
- [ ] Job state transitions are explicit, deterministic and fail closed for unknown, stale or
  illegal transitions.
- [ ] Persistent jobs, attempts and leases use the governed SQLite Runtime Store with forward-only
  migration, bounded retention and transactional writes.
- [ ] Atomic claiming, renewable leases and fencing prevent duplicate concurrent execution after
  worker contention, crash or restart.
- [ ] Retry count, exponential backoff, jitter, deadline and maximum elapsed time are bounded and
  enforced before dispatch.
- [ ] Cancellation, timeout and shutdown are cooperative, bounded and recorded without silently
  converting an uncertain outcome into success.
- [ ] Recurring schedules prevent unbounded catch-up, clock-skew loops and duplicate fire times.
- [ ] Worker concurrency, queue capacity, polling interval and batch size have explicit limits.
- [ ] Job payloads, errors and inspection output cannot expose secrets, prompts, filesystem paths,
  provider payloads or arbitrary private values.
- [ ] Every scheduling, claim, dispatch, retry, cancellation, timeout and terminal outcome emits a
  canonical redacted Runtime Observability event.
- [ ] Runtime Metrics and Health Monitoring receives bounded scheduler and worker signals without
  acquiring scheduling or execution authority.
- [ ] Query and management operations require canonical Agent identity and the existing minimum
  permissions; unauthorized operations fail before repository mutation.
- [ ] CLI supports bounded schedule/job create, list, describe, cancel and worker dry-run or
  inspection operations in human-readable and JSON formats.
- [ ] Recovery tests cover restart, expired leases, duplicate claims, interrupted attempts and
  persistence reopen without replaying completed work.
- [ ] Existing Controller, Execution, Workflow, Tool, Adapter, persistence, observability and
  monitoring public APIs remain compatible.
- [ ] Positive, negative, authorization, concurrency, recovery, timeout and redaction tests exist.
- [ ] Tests pass on Python 3.11 and Python 3.12.
- [ ] Coverage remains at or above the configured 80% threshold.
- [ ] Control Plane Consistency Check has no new blocking finding.
- [ ] Whole-branch Reviewer result is APPROVE.
- [ ] Protected Pull Request governance passes before merge.

Proposed Artifacts:
- CR-2026-016
- Proposed `feature/runtime-scheduler-background-jobs`
- Proposed `src/ai_os/scheduler/`
- Proposed `tests/scheduler/`
- Proposed governed SQLite scheduler migration
- Proposed CLI integration for schedule, job and worker inspection

Risks:
- Duplicate claims or stale workers could execute the same external side effect more than once.
- Scheduler dispatch could become a second Controller or bypass Task and approval gates.
- Unbounded retries, recurrence or catch-up could cause runaway execution and cost.
- Clock skew, process crashes and expired leases could corrupt job state or lose work.
- Stored payloads and failure details could expose private or provider data.
- Background workers could weaken cancellation, shutdown and audit guarantees.

Notes:
- Change ID: CR-2026-016.
- Requester: Repository Owner.
- Date: 2026-09-21.
- Target Document: `ARCHITECTURE.md`, `WORKFLOW.md`, `TASKS.md` and executable runtime modules.
- Change Type: ARCHITECTURE / WORKFLOW / SECURITY / PERSISTENCE.
- Classification: MAJOR runtime capability with concurrency, persistence and external side-effect
  risk.
- Reason: Add durable scheduled and background execution above the installed Controller,
  Workflow, Execution, persistence, observability and monitoring layers.
- Current State: AI OS can execute governed workflows and inspect runtime health, but it cannot
  durably schedule future work, coordinate background workers or recover leased jobs.
- Proposed Change: Add a bounded persistent scheduler and worker boundary that dispatches only
  through existing governance and execution authority.
- Affected Documents: `ARCHITECTURE.md`, `WORKFLOW.md`, `TASKS.md`.
- Affected Agents: Controller, Planner, Developer, Tester, Reviewer and Fixer.
- Dependencies: TASK-0005, TASK-0006, TASK-0010, TASK-0011, TASK-0013, TASK-0014, TASK-0015,
  TASK-0017 and TASK-0018.
- Approval Required: Explicit A2 Human Approval before implementation.
- Approval Evidence: Repository Owner issued `APPROVE CR-2026-016` on 2026-09-21.
- CR Status: APPROVED / IMPLEMENTATION AUTHORIZED.
- Implementation may begin on a dedicated feature branch only after this approval record is merged
  to authoritative `main`; TASK-0019 remains `TODO` until that branch is created.

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
