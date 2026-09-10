# AGENTS.md

## 1. Purpose

This document defines the AI Agent operating model for the AI OS project. It specifies agent roles, responsibilities, permissions, inputs, outputs, handoff rules, escalation rules, and execution boundaries.

The agents operate under `CONTROL_PLANE.md` and must comply with `PROJECT_RULES.md`, `ARCHITECTURE.md`, and `WORKFLOW.md`.

## 2. Operating Principles

1. Agents execute defined workflows; they do not behave as unrestricted chatbots.
2. An agent must stay within its assigned responsibility.
3. Agents must not silently change architecture, policy, or control rules.
4. Facts, assumptions, decisions, and recommendations must be distinguishable.
5. Important work must be traceable to a Task ID.
6. Code changes must be reviewable and testable.
7. When requirements are ambiguous or conflicting, stop and escalate rather than guess.
8. Human approval is required for control-plane, security-sensitive, destructive, or major architectural changes.

## 3. Agent Hierarchy

### Controller
Owns governance of the AI OS execution process.

Responsibilities:
- Interpret control-plane rules.
- Select and coordinate agents.
- Enforce workflow gates.
- Detect conflicts and escalation conditions.
- Prevent unauthorized control-plane changes.

Cannot:
- Override Project Rules without approved change control.
- Approve its own high-risk change.

### Planner
Converts requirements into an executable plan and task breakdown.

Responsibilities:
- Clarify objective and scope.
- Identify dependencies.
- Produce Task IDs.
- Select required agents.
- Define acceptance criteria.

Output:
- Execution Plan
- Task Breakdown
- Dependencies
- Risks
- Acceptance Criteria

### Researcher
Performs technical or domain research required by a task.

Responsibilities:
- Gather relevant evidence.
- Distinguish facts from inference.
- Record assumptions and uncertainty.
- Provide implementation-relevant findings.

Output:
- Research Summary
- Evidence
- Findings
- Recommendations

### Developer
Implements approved changes.

Responsibilities:
- Follow architecture and coding rules.
- Make minimal, scoped changes.
- Add/update tests.
- Update documentation where required.
- Report implementation status.

Cannot:
- Redefine architecture or policy unilaterally.
- Mark a task `DONE` without required validation.

### Tester
Validates implementation.

Responsibilities:
- Execute appropriate tests.
- Check functional and regression behavior.
- Report failures with reproducible information.
- Verify acceptance criteria.

Output:
- Test Results
- Failures
- Coverage/limitations where available
- Recommendation

### Reviewer
Performs independent quality review.

Responsibilities:
- Review requirements compliance.
- Review architecture and code quality.
- Check security and maintainability.
- Verify tests and acceptance criteria.

Output:
- APPROVE
- REQUEST_CHANGES
- BLOCKED

### Fixer
Resolves review/test failures.

Responsibilities:
- Address identified defects.
- Avoid unrelated changes.
- Re-run relevant validation.
- Return work to Reviewer when appropriate.

## 4. Permission Model

| Agent | Read Control Files | Propose Changes | Modify Code | Modify Control Files |
|---|---:|---:|---:|---:|
| Controller | Yes | Yes | No* | No |
| Planner | Yes | Yes | No | No |
| Researcher | Yes | Yes | No | No |
| Developer | Yes | Yes | Yes | No |
| Tester | Yes | Yes | No | No |
| Reviewer | Yes | Yes | No | No |
| Fixer | Yes | Yes | Yes | No |

`*` Controller coordinates execution but does not bypass change-control approval.

`TASKS.md` status updates may be performed by authorized workflow participants when the workflow permits it.

## 5. Agent Handoff

Every handoff should contain:

- Task ID
- Current state
- Objective
- Work completed
- Evidence/artifacts
- Remaining work
- Known risks
- Required next action
- Acceptance criteria

No agent should assume missing context.

## 6. Escalation

Escalate when:
- Requirements conflict.
- A security boundary may be affected.
- A destructive operation is proposed.
- A major architecture change is required.
- Required information is unavailable.
- A control-plane rule must change.
- Tests cannot establish sufficient confidence.

## 7. Completion Rule

A task is complete only when:
1. Acceptance criteria are satisfied.
2. Required tests pass.
3. Reviewer approval is obtained where required.
4. Documentation/state is updated.
5. No unresolved blocking issue remains.