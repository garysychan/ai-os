# CONTROL_PLANE.md

> AI OS Project — Control Plane Controller  
> Version: 1.0.0  
> Status: ACTIVE  
> Authority: Project Governance

---

## 1. Purpose

`CONTROL_PLANE.md` is the governance controller for the AI OS Project.

It does not replace the five core control documents. It defines how they are governed, versioned, changed, approved, validated, and interpreted.

The five controlled documents are:

1. `AGENTS.md`
2. `PROJECT_RULES.md`
3. `ARCHITECTURE.md`
4. `WORKFLOW.md`
5. `TASKS.md`

The Control Plane is designed for the project's:

- AI OS
- Coding workflow
- Codex execution
- GitHub repository
- Agent-based development model

---

# 2. Control Plane Objectives

The Control Plane must ensure:

1. Consistent Project governance.
2. Explicit authority and ownership.
3. Controlled changes to rules and architecture.
4. Human approval for high-impact changes.
5. Traceable agent execution.
6. Consistency between agents, rules, architecture, workflow, and tasks.
7. Versioned evolution of the Project.
8. No silent policy or architecture changes.

---

# 3. Controlled Document Registry

| Document | Domain | Primary Responsibility | Change Level |
|---|---|---|---|
| `CONTROL_PLANE.md` | Governance | Control Plane | Critical |
| `AGENTS.md` | Agents | Agent model | High |
| `PROJECT_RULES.md` | Policy | Engineering / AI rules | Critical |
| `ARCHITECTURE.md` | Architecture | System design | Critical |
| `WORKFLOW.md` | Execution | Execution lifecycle | High |
| `TASKS.md` | State | Current work | Normal |

`CONTROL_PLANE.md` governs the management of the other five documents.

For a ChatGPT Free Project, the recommended Project file set is:

```text
CONTROL_PLANE.md
AGENTS.md
PROJECT_RULES.md
ARCHITECTURE.md
WORKFLOW.md
```

`TASKS.md` should preferably be maintained in the GitHub repository as durable project state.

---

# 4. Authority Model

The Project has domain-specific authority rather than a simplistic file hierarchy.

| Decision Domain | Authoritative Document |
|---|---|
| Governance | `CONTROL_PLANE.md` |
| Agent roles / permissions | `AGENTS.md` |
| Mandatory project rules | `PROJECT_RULES.md` |
| System architecture | `ARCHITECTURE.md` |
| Execution workflow | `WORKFLOW.md` |
| Task state | `TASKS.md` |

When two documents appear to conflict:

1. Identify the domain of the conflicting rule.
2. Identify the authoritative document for that domain.
3. Check whether the conflict is caused by an outdated document.
4. Do not silently select a rule.
5. Create a Change Request if reconciliation is required.
6. Block affected execution when the conflict could cause material harm.

---

# 5. Operating Modes

The Control Plane supports three execution modes.

## QUICK

For low-risk, well-defined tasks.

Requirements:
- Existing rules remain unchanged.
- No major architecture change.
- Appropriate validation still required.

## STANDARD

Default mode.

Flow:

```text
Requirement
→ Analysis
→ Planning
→ Execution
→ Testing
→ Review
→ Validation
→ Completion
```

## DEEP

For complex research, architecture, high-risk coding, or cross-system changes.

Requirements:
- Expanded analysis.
- Dependency analysis.
- Risk analysis.
- Stronger validation.
- Explicit assumptions and uncertainty.

No mode may bypass mandatory security or approval gates.

---

# 6. Permission Model

## 6.1 Control Plane Files

Default permissions:

| Actor | Read | Propose | Direct Modify |
|---|---:|---:|---:|
| Human | YES | YES | YES |
| Controller | YES | YES | NO |
| Planner | YES | YES | NO |
| Researcher | YES | YES | NO |
| Developer | YES | YES | NO |
| Tester | YES | YES | NO |
| Reviewer | YES | YES | NO |
| Fixer | YES | YES | NO |

Agents may produce a proposed replacement or patch, but the proposal must pass the applicable approval gate before the authoritative file is changed.

## 6.2 TASKS.md

`TASKS.md` has a different permission model.

Agents may update:

- Status
- Execution notes
- Test results
- Handoff information

provided the update follows `WORKFLOW.md`.

Agents may not silently change:

- Project scope
- Architecture
- Priority of critical work
- Acceptance criteria with material impact
- Governance rules

Such changes require Change Control.

---

# 7. Change Request Protocol

Every material Control Plane change begins with a Change Request.

## 7.1 Change Request ID

Use:

```text
CR-YYYY-NNN
```

Example:

```text
CR-2026-001
```

## 7.2 Required Fields

```text
Change ID:
Requester:
Date:
Target Document:
Change Type:
Reason:
Current Rule / State:
Proposed Change:
Affected Documents:
Affected Agents:
Impact:
Risk:
Dependencies:
Approval Required:
Status:
```

## 7.3 Change Types

Allowed types:

- GOVERNANCE
- AGENT
- POLICY
- ARCHITECTURE
- WORKFLOW
- TASK
- SECURITY
- INTEGRATION
- DOCUMENTATION

---

# 8. Change Classification

## PATCH

Use for:
- Typographical corrections.
- Clarifications that do not alter behavior.
- Non-semantic documentation corrections.

Approval:
- Reviewer or designated maintainer.

## MINOR

Use for:
- New non-breaking capability.
- New workflow step.
- New agent responsibility.
- New optional rule.
- Compatible architecture extension.

Approval:
- Human approval recommended.
- Required when security or production behavior is affected.

## MAJOR

Use for:
- Governance changes.
- Permission changes.
- Breaking architecture changes.
- Breaking workflow changes.
- Removal or replacement of core agents.
- Security boundary changes.
- Changes that invalidate existing tasks or integrations.

Approval:
- Explicit human approval REQUIRED.

---

# 9. Change Lifecycle

The canonical Change Control lifecycle is:

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
IMPLEMENTATION
      ↓
CONSISTENCY CHECK
      ↓
VERSION UPDATE
      ↓
CHANGE CLOSED
```

No agent may skip the applicable gate.

---

# 10. Approval Protocol

The approval keyword is:

```text
APPROVE CR-YYYY-NNN
```

Examples:

```text
APPROVE CR-2026-001
```

For a proposed Control Plane rebuild:

```text
APPROVE REBUILD
```

Approval must be explicit.

Statements such as:

- "looks good"
- "probably fine"
- "go ahead?"

must not be interpreted as formal approval for a high-impact Control Plane change.

---

# 11. Approval Levels

### A0 — No Approval

Examples:
- Typographical correction.
- Formatting correction.
- Non-semantic documentation improvement.

### A1 — Agent / Reviewer Approval

Examples:
- Low-risk task-state correction.
- Minor implementation documentation update.

### A2 — Human Approval

Required for:
- Rules.
- Agent permissions.
- Workflow gates.
- Architecture changes.
- Security-sensitive changes.

### A3 — Explicit Human Approval

Required for:
- Control Plane governance.
- Major architecture changes.
- Breaking changes.
- Destructive operations.
- Production-impacting changes.
- Permission escalation.

---

# 12. Control Plane Modification Rule

Agents must NEVER silently modify:

```text
CONTROL_PLANE.md
PROJECT_RULES.md
AGENTS.md
ARCHITECTURE.md
WORKFLOW.md
```

Instead:

```text
READ
 ↓
ANALYZE
 ↓
PROPOSE
 ↓
APPROVE
 ↓
MODIFY
 ↓
VALIDATE
```

If approval is required and unavailable:

```text
BLOCKED
```

---

# 13. Consistency Check

After any material change, run:

```text
CONTROL PLANE CONSISTENCY CHECK
```

## 13.1 Required Checks

### CP-C01 — Required Files

Verify that all required Control Plane files exist.

### CP-C02 — Cross References

Verify that referenced files, agents, states, and concepts exist.

### CP-C03 — Agent Consistency

Verify:

- Agents referenced by Workflow exist in `AGENTS.md`.
- Agent permissions are consistent.
- Agent responsibilities do not conflict.

### CP-C04 — Workflow Consistency

Verify:

- Workflow states are defined.
- State transitions are valid.
- Required gates exist.
- Agents assigned to stages exist.

### CP-C05 — Architecture Consistency

Verify:

- Workflow is compatible with architecture.
- Agent runtime assumptions match architecture.
- GitHub/Codex integration assumptions are documented.

### CP-C06 — Rules Consistency

Verify:

- No contradictory rules.
- Security requirements are not weakened.
- Quality gates are not bypassed.

### CP-C07 — Task Consistency

Verify:

- Task states are valid.
- Tasks reference valid agents.
- Dependencies are valid.
- Acceptance criteria are present for executable tasks.

### CP-C08 — Permission Consistency

Verify that no agent has unauthorized direct modification rights.

### CP-C09 — Version Consistency

Verify that document versions and Control Plane version are compatible.

### CP-C10 — Orphan Detection

Detect:

- Undefined agents.
- Undefined workflow states.
- Undefined Task IDs.
- Dead references.
- Unused control rules.

---

# 14. Consistency Result

The checker must return one of:

```text
PASS
WARNING
FAIL
```

## PASS

No blocking inconsistency detected.

## WARNING

Non-blocking issue exists.

Example:

```text
WARNING:
TASK-0007 references a proposed component not yet implemented.
```

## FAIL

Execution must stop when the inconsistency could materially affect correctness, security, governance, or architecture.

Example:

```text
FAIL:
Developer Agent is granted direct modification permission
for PROJECT_RULES.md.
```

---

# 15. Conflict Resolution

When a conflict is detected:

```text
CONFLICT DETECTED
       ↓
STOP AFFECTED EXECUTION
       ↓
IDENTIFY DOMAIN
       ↓
IDENTIFY AUTHORITATIVE DOCUMENT
       ↓
CREATE CHANGE REQUEST
       ↓
REVIEW
       ↓
APPROVAL
       ↓
RECONCILE DOCUMENTS
       ↓
CONSISTENCY CHECK
```

Agents must not resolve material conflicts through silent assumptions.

---

# 16. Versioning

Control Plane version format:

```text
MAJOR.MINOR.PATCH
```

## MAJOR

Increment when:
- Governance model changes.
- Permission model changes.
- Core architecture changes.
- Core workflow becomes incompatible.
- Existing integrations require breaking changes.

Example:

```text
1.4.2 → 2.0.0
```

## MINOR

Increment when:
- Compatible capabilities are added.
- New agent responsibilities are introduced.
- New workflow stages are added without breaking existing execution.

Example:

```text
1.4.2 → 1.5.0
```

## PATCH

Increment when:
- Typos are corrected.
- Clarifications are made.
- Non-semantic documentation is improved.

Example:

```text
1.4.2 → 1.4.3
```

---

# 17. Version Matrix

Every controlled file should declare:

```text
Control Plane Version:
Document Version:
Status:
Last Updated:
```

Example:

```text
Control Plane Version: 1.0.0
Document Version: 1.0.0
Status: ACTIVE
```

A material update must preserve traceability between the Control Plane version and affected document versions.

---

# 18. GitHub Source of Truth

For the engineering repository:

```text
GitHub
   ↓
Source Control
   ↓
Version History
   ↓
Pull Request / Review
   ↓
Durable Project State
```

Recommended repository location:

```text
ai-os/
├── CONTROL_PLANE.md
├── AGENTS.md
├── PROJECT_RULES.md
├── ARCHITECTURE.md
├── WORKFLOW.md
├── TASKS.md
├── agents/
├── skills/
├── workflows/
├── scripts/
├── src/
├── tests/
└── .github/
```

The ChatGPT Project provides operational context and a lightweight Control Plane workspace.

GitHub provides durable version-controlled project state.

When the two disagree, the discrepancy must be surfaced and reconciled; it must not be silently ignored.

---

# 19. Codex Governance

Codex is an execution layer, not the owner of Project governance.

Codex may:

- Inspect repository state.
- Implement approved code tasks.
- Run tests.
- Refactor code within approved scope.
- Prepare commits/PRs.
- Report implementation results.

Codex must not:

- Bypass Project Rules.
- Change Control Plane governance without approval.
- Invent architecture decisions.
- Skip required tests.
- Hide failed validation.
- Commit secrets.

Typical Codex lifecycle:

```text
TASK
 ↓
READ CONTROL PLANE
 ↓
INSPECT REPOSITORY
 ↓
PLAN
 ↓
IMPLEMENT
 ↓
TEST
 ↓
REVIEW
 ↓
FIX
 ↓
VALIDATE
 ↓
COMMIT / PR
```

---

# 20. GitHub Change Governance

For material engineering changes:

```text
Task
 ↓
Branch
 ↓
Implementation
 ↓
Tests
 ↓
Commit
 ↓
Pull Request
 ↓
Review
 ↓
Merge
```

The exact GitHub branching strategy may evolve through approved architecture/workflow changes.

Control Plane files should be reviewed as governance artifacts when their behavior changes.

---

# 21. Human-in-the-Loop Rules

Human intervention is mandatory when:

- Requirements are materially ambiguous.
- Rules conflict.
- Security is affected.
- Credentials or permissions are involved.
- Production impact is possible.
- Destructive operations are proposed.
- Architecture changes are major.
- A Control Plane file must change.
- An agent requests authority outside its permission boundary.

The AI OS should prefer:

```text
BLOCK + ESCALATE
```

over:

```text
GUESS + EXECUTE
```

---

# 22. Emergency Stop

Any agent may request an execution stop when it detects:

- Security risk.
- Data loss risk.
- Unauthorized permission escalation.
- Irreversible destructive action.
- Control Plane corruption.
- Critical inconsistency.

Emergency state:

```text
STOPPED
```

Resume requires an explicit decision by an authorized human or approved recovery process.

---

# 23. Control Plane Bootstrap

When initializing or rebuilding the Control Plane:

```text
1. Read Project Instructions.
2. Read all available Control Plane files.
3. Analyze current state.
4. Detect conflicts.
5. Produce Rebuild Proposal.
6. Wait for approval.
7. Generate/update files.
8. Run Consistency Check.
9. Report final status.
```

Never overwrite existing governance blindly.

---

# 24. Standard Commands

The following natural-language commands are recognized by the Project workflow.

### Analyze

```text
ANALYZE CONTROL PLANE
```

### Propose Change

```text
CREATE CHANGE REQUEST
```

### Approve Change

```text
APPROVE CR-YYYY-NNN
```

### Check Consistency

```text
CHECK CONTROL PLANE
```

### Rebuild

```text
REBUILD CONTROL PLANE
```

### Approve Rebuild

```text
APPROVE REBUILD
```

### Status

```text
CONTROL PLANE STATUS
```

These are workflow conventions, not application commands, unless an implementation explicitly maps them to executable functions.

---

# 25. Control Plane Status Report

A standard status report should contain:

```text
CONTROL PLANE STATUS

Version:
Status:
Files:
Consistency:
Open Change Requests:
Blocked Tasks:
Architecture Status:
Workflow Status:
Security Status:
GitHub Sync Status:
Codex Readiness:
```

Possible overall statuses:

```text
READY
WARNING
BLOCKED
```

---

# 26. Definition of a Healthy Control Plane

The Control Plane is `READY` when:

- Required documents exist.
- No blocking conflict exists.
- Agent permissions are defined.
- Workflow states are valid.
- Rules are internally consistent.
- Architecture is coherent.
- Tasks are traceable.
- Change control is operational.
- Required approval gates are defined.
- GitHub/Codex responsibilities are clear.

---

# 27. Current Baseline

```text
Control Plane Version: 1.0.0
Status: ACTIVE

Controlled Documents:
- AGENTS.md
- PROJECT_RULES.md
- ARCHITECTURE.md
- WORKFLOW.md
- TASKS.md

Execution Model:
AI OS + Agents + Codex + GitHub

Default Workflow:
Requirement
→ Analysis
→ Planning
→ Task Breakdown
→ Execution
→ Testing
→ Review
→ Fix
→ Validation
→ Completion

Governance Model:
Human approval for material Control Plane, policy,
architecture, security, permission, and destructive changes.
```

---

# 28. Final Governance Principle

The AI OS must remain:

```text
Governed
Traceable
Reviewable
Testable
Versioned
Recoverable
Human-controlled
```

The Control Plane exists to prevent the system from becoming an uncontrolled collection of prompts, agents, scripts, and code.

It establishes the boundary between:

```text
WHAT MAY CHANGE
       ↓
WHO MAY CHANGE IT
       ↓
HOW IT MAY CHANGE
       ↓
WHO MUST APPROVE IT
       ↓
HOW THE CHANGE IS VERIFIED
```

This is the governing contract for the AI OS Project.