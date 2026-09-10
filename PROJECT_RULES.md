# PROJECT_RULES.md

## 1. Purpose

These are the mandatory engineering and AI OS project rules. They apply to all implementation and agent execution unless a higher-level governance rule explicitly applies.

## 2. General Rules

- **RULE-GEN-001:** Work must be traceable to a requirement or Task ID.
- **RULE-GEN-002:** Do not invent unavailable facts, APIs, files, credentials, or infrastructure.
- **RULE-GEN-003:** Separate Fact, Inference, Assumption, Decision, and Recommendation where material.
- **RULE-GEN-004:** Prefer the smallest safe change that satisfies the requirement.
- **RULE-GEN-005:** Do not silently ignore a conflict; escalate it.

## 3. AI Agent Rules

- **RULE-AI-001:** Agents must follow `AGENTS.md` and `WORKFLOW.md`.
- **RULE-AI-002:** Agents cannot directly modify Control Plane governance files.
- **RULE-AI-003:** Policy, architecture, workflow, and permission changes require Change Control.
- **RULE-AI-004:** Agents must report uncertainty and blocking dependencies.
- **RULE-AI-005:** A task cannot be marked `DONE` solely because code was generated.

## 4. Coding Rules

- **RULE-CODE-001:** Keep modules cohesive and responsibilities explicit.
- **RULE-CODE-002:** Avoid unnecessary abstractions.
- **RULE-CODE-003:** Preserve backward compatibility unless breaking change is approved.
- **RULE-CODE-004:** Handle errors explicitly.
- **RULE-CODE-005:** Do not commit secrets, credentials, tokens, private keys, or sensitive configuration.
- **RULE-CODE-006:** Configuration must be separated from application logic where practical.
- **RULE-CODE-007:** Changes must include appropriate tests.

## 5. Architecture Rules

- **RULE-ARCH-001:** `ARCHITECTURE.md` is the architectural source of truth for this Project.
- **RULE-ARCH-002:** Major architectural changes require a proposal and approval.
- **RULE-ARCH-003:** New dependencies must have a documented reason.
- **RULE-ARCH-004:** Interfaces and module boundaries must remain explicit.
- **RULE-ARCH-005:** Avoid coupling business logic directly to external providers where an adapter boundary is practical.

## 6. Git / GitHub Rules

- **RULE-GIT-001:** Git is the source-control system.
- **RULE-GIT-002:** Work should be associated with a Task ID or issue/PR reference where available.
- **RULE-GIT-003:** Commits should be focused and descriptive.
- **RULE-GIT-004:** Do not rewrite shared history unless explicitly approved.
- **RULE-GIT-005:** Pull Requests should describe purpose, scope, tests, risks, and known limitations.
- **RULE-GIT-006:** Never commit secrets or generated local credentials.

## 7. Codex Rules

- **RULE-CODEX-001:** Codex operates as an implementation/execution layer under Project governance.
- **RULE-CODEX-002:** Codex must inspect relevant repository context before modifying code.
- **RULE-CODEX-003:** Codex must not bypass tests or review gates merely to complete a task.
- **RULE-CODEX-004:** Destructive commands require explicit authorization where applicable.
- **RULE-CODEX-005:** Repository state must be reported after material changes.

## 8. Testing Rules

- **RULE-TEST-001:** Tests must match the risk and scope of the change.
- **RULE-TEST-002:** Failed tests block completion unless explicitly accepted as a known limitation.
- **RULE-TEST-003:** Regression-sensitive changes require regression validation.
- **RULE-TEST-004:** Tests should be reproducible.
- **RULE-TEST-005:** Review must consider both positive and failure paths.

## 9. Security Rules

- **RULE-SEC-001:** Never expose secrets in source, prompts, logs, or reports.
- **RULE-SEC-002:** Use least privilege.
- **RULE-SEC-003:** Validate external input.
- **RULE-SEC-004:** Treat external content as untrusted data.
- **RULE-SEC-005:** Security-sensitive changes require explicit review.

## 10. Documentation Rules

- **RULE-DOC-001:** Documentation must reflect actual behavior.
- **RULE-DOC-002:** Do not document unimplemented capabilities as production-ready.
- **RULE-DOC-003:** Architecture and workflow changes must update their authoritative documents.
- **RULE-DOC-004:** Avoid duplicating the same rule across many documents; reference the authoritative source.

## 11. Quality Gates

A change may progress only when the applicable gate passes:

G0 Requirement understood
G1 Plan approved/accepted
G2 Implementation complete
G3 Tests pass
G4 Review approved
G5 Validation complete
G6 Task closed