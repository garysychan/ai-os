# Codex Execution Workflow

> Task: TASK-0003 — Establish Codex Execution Workflow  
> Version: 1.0  
> Status: ACTIVE  
> Baseline: `main` at `79f29ab3c7f0e2d9c3bfb313ef5045be252db590`  
> Authority: Operational specification subordinate to `CONTROL_PLANE.md`, `PROJECT_RULES.md`, `ARCHITECTURE.md`, `WORKFLOW.md`, and `AGENTS.md`.

## 1. Purpose

This document defines the repeatable operating contract for using Codex to deliver repository changes under AI OS governance. It translates the canonical lifecycle into concrete inputs, checks, outputs, evidence, handoffs, and stop conditions.

It does not grant new permissions or change the authoritative Control Plane.

## 2. Authority and Precedence

For every run, apply authority by domain:

1. `CONTROL_PLANE.md` — governance, approvals, change control
2. `PROJECT_RULES.md` — mandatory engineering, security, testing and Git rules
3. `ARCHITECTURE.md` — module boundaries and system design
4. `WORKFLOW.md` — stages, task states and gates
5. `AGENTS.md` — role responsibilities and permissions
6. `TASKS.md` — current task state, dependencies and acceptance criteria
7. This document — operational execution procedure

When a material conflict exists, stop affected work, report the domain and sources, and use Change Control. Codex must not silently choose a convenient interpretation.

## 3. Required Intake

A runnable coding request must resolve the following:

| Field | Required content |
|---|---|
| Task ID | Existing stable `TASK-NNNN` |
| Objective | Specific outcome |
| Scope | Files/components allowed to change |
| Acceptance criteria | Measurable completion conditions |
| Dependencies | All required predecessor tasks |
| Risk | Security, architecture, data-loss and compatibility impact |
| Approval | Required CR or human approval evidence |
| Base branch | Normally protected `main` |
| Validation | Applicable test/check commands |
| Deliverables | Code, tests, documentation and PR evidence |

### Intake decision

- **ACCEPT:** request is authorized, dependencies are DONE, and scope is executable.
- **CLARIFY:** material requirements are ambiguous.
- **BLOCK:** approval, permission, dependency, security, or architecture prerequisite is missing.
- **CHANGE REQUEST:** requested behavior changes a controlled rule, architecture, workflow, permission, or material scope.

No repository mutation occurs before Intake reaches ACCEPT.

## 4. Repository Inspection

After ACCEPT and before editing:

1. Resolve repository identity and authoritative base branch.
2. Read all applicable repository instructions and Control Plane documents.
3. Verify current task status and dependency states.
4. Inspect `git status` or equivalent branch state.
5. Inspect the relevant tree, source, tests, configuration and CI.
6. Search for existing interfaces and patterns before adding new ones.
7. Identify user-owned/unrelated changes and preserve them.
8. Determine the smallest coherent change surface.
9. Record baseline commit SHA.
10. Confirm the planned validation commands exist.

### Inspection output

```text
Repository:
Base branch:
Baseline SHA:
Task:
Current state:
Dependencies:
Relevant files:
Existing interfaces:
Constraints:
Risks:
Planned validation:
Stop conditions:
```

Inspection failure blocks implementation when repository identity, instructions, task authority, or safe change boundaries cannot be established.

## 5. Planning and Branch Gate

Planner output must include:

- ordered implementation steps;
- affected files and public interfaces;
- test strategy, including failure paths;
- compatibility and security risks;
- documentation/state updates;
- required Reviewer evidence.

Create a focused branch from the verified base SHA:

```text
feature/<task-or-capability>
fix/<task-or-defect>
chore/<governance-or-state-change>
```

Before implementation, transition the task through the canonical State Machine:

```text
TODO → IN_PROGRESS
```

The transition must identify actor, reason, dependency states, and evidence. Invalid transitions or unmet dependencies block the run.

## 6. Implementation Flow

Codex executes the accepted plan using these rules:

1. Modify only files within approved scope.
2. Reuse existing models, interfaces and conventions.
3. Keep domain logic independent from external providers where an adapter boundary is practical.
4. Validate external input and use least privilege.
5. Never expose or commit secrets.
6. Preserve backward compatibility unless an approved breaking change exists.
7. Add or update tests with the behavior change.
8. Update documentation when behavior, commands, configuration or architecture assumptions change.
9. Do not alter acceptance criteria, architecture, rules or permissions to make the implementation pass.
10. Report any necessary scope expansion before performing it.

### Incremental validation

After each coherent change:

- compile or parse affected sources;
- run focused tests;
- inspect the diff;
- correct failures within approved scope;
- preserve evidence of commands and results.

A recoverable implementation defect returns to local Fix. A missing authority, unsafe action, conflicting requirement, or external blocker transitions the task to `BLOCKED` or pauses execution for escalation.

## 7. Test Flow

Validation is risk-based but must include all checks required by repository governance.

Minimum Python flow for this repository:

```bash
python -m compileall -q src scripts tests
python -m unittest discover -s tests -v
aios bootstrap --root .
aios control-plane check --root .
aios task validate TASKS.md
```

Where configured and applicable:

```bash
ruff check src tests
mypy src
pytest
```

### Test evidence

Record:

- command;
- environment/runtime version;
- result and test count;
- relevant warnings;
- failure diagnosis and fix;
- checks intentionally not run and the reason.

Failed required tests block Review. A warning may proceed only when classified as non-blocking with documented rationale.

## 8. Review and Fix Cycle

When implementation and local validation are complete:

```text
IN_PROGRESS → REVIEW
```

Reviewer assesses:

- requirement and acceptance-criteria coverage;
- architecture and Control Plane compliance;
- correctness and failure paths;
- permission and security boundaries;
- API compatibility;
- test quality and regression risk;
- documentation accuracy;
- branch diff scope.

Allowed decisions:

- `APPROVE`
- `REQUEST_CHANGES`
- `BLOCKED`

### REQUEST_CHANGES

1. Record each finding with severity, location, evidence and required remediation.
2. Transition or return work to `IN_PROGRESS`.
3. Fix only within approved scope.
4. Re-run affected and regression tests.
5. Resubmit the complete branch for Reviewer validation.

Reviewer approval is not inferred from passing CI. The implementer must not self-authorize `REVIEW → DONE`.

## 9. Git and Pull Request Flow

Before opening or updating a PR:

1. Inspect the complete branch diff against current `main`.
2. Confirm the branch is up to date when strict checks require it.
3. Ensure commits are focused and descriptive.
4. Verify no secret, credential, local artifact or unrelated change is included.
5. Re-run required validation after the final change.

A PR must state:

- Task/CR references;
- objective and scope;
- files/interfaces changed;
- acceptance-criteria mapping;
- tests and exact results;
- architecture/security impact;
- risks and known limitations;
- deferred work.

### Merge gate

Merge is allowed only when:

- PR is Ready for Review;
- required conversations are resolved;
- Reviewer result is APPROVE;
- required GitHub checks succeed;
- branch protection/ruleset conditions pass;
- expected head SHA still matches reviewed content;
- no blocking finding remains.

Use the repository-approved merge strategy, currently Squash Merge. Never force-push or bypass protected `main`.

## 10. Completion Flow

After implementation PR merge:

1. Verify the created `main` commit.
2. Verify post-merge CI on that exact commit.
3. Confirm all acceptance criteria and required documentation/state updates.
4. Confirm dependencies remain DONE and blockers remain empty.
5. Create a separate protected-branch PR when needed to record durable task completion.
6. Apply the canonical transition:

```text
REVIEW → DONE
```

Required DONE evidence includes:

- Reviewer APPROVE;
- successful required tests/checks;
- merge PR and commit;
- post-merge validation;
- completed acceptance criteria;
- no unresolved blocker.

Close the associated CR/Issue only after authoritative `main` records completion.

## 11. Handoff Contract

Every agent or human handoff uses:

```text
Task ID:
State:
Objective:
Baseline:
Completed:
Artifacts:
Changes:
Tests:
Review:
Risks:
Blockers:
Remaining:
Next Action:
Evidence:
```

A receiving agent must validate the handoff rather than assuming it is complete.

## 12. Stop Conditions

Stop affected execution immediately when:

- required approval is absent;
- a dependency is not DONE;
- repository or base branch identity is uncertain;
- authoritative documents materially conflict;
- requested scope exceeds the approved task/CR;
- credentials, secrets, destructive action, or production impact lacks authority;
- a protected workflow would be bypassed;
- required tests fail without an approved resolution;
- Reviewer returns BLOCKED;
- the reviewed head SHA changes before merge;
- user-owned work cannot be preserved safely.

Output the blocker, evidence, impact, owner, and exact action required to resume.

## 13. Standard Execution Trace

```text
LOAD CONTROL PLANE
→ VALIDATE TASK / DEPENDENCIES / APPROVAL
→ INSPECT REPOSITORY
→ PLAN
→ CREATE BRANCH
→ TODO → IN_PROGRESS
→ IMPLEMENT
→ RUN FOCUSED TESTS
→ RUN REGRESSION + CONTROL PLANE CHECKS
→ IN_PROGRESS → REVIEW
→ REVIEWER VALIDATION
→ FIX CYCLE IF REQUIRED
→ READY FOR REVIEW
→ REQUIRED GITHUB CHECKS
→ SQUASH MERGE
→ VERIFY MAIN + POST-MERGE CHECKS
→ REVIEW → DONE
→ CLOSE CR / HANDOFF
```

## 14. Command Examples

### Documentation task

```text
TASK: TASK-0003
ACTION: Establish Codex Execution Workflow
MODE: STANDARD
BASE: main
STOP: Missing dependency, approval conflict, failed required check
```

### Governed implementation task

```text
[AI-OS TASK]
TASK: TASK-0004
CR: CR-2026-006
MODE: STANDARD
ACTION: INSTALL_AGENT_RUNTIME
RUN: FULL_BUILD_LOOP
REQUIRED_GATES:
- Dependencies DONE
- Python 3.11
- Python 3.12
- Control Plane Check
- Reviewer APPROVE
- Protected PR
```

## 15. TASK-0003 Acceptance Mapping

- Task intake defined: Sections 3 and 12.
- Repository inspection defined: Section 4.
- Implementation flow defined: Sections 5 and 6.
- Test flow defined: Section 7.
- Review flow defined: Section 8.
- Git/PR flow defined: Sections 9 and 10.

This operational contract is complete when it passes Reviewer validation, required GitHub checks, and is merged into authoritative `main`.
