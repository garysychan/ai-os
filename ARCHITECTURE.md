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