"""Immutable domain models for the provider-neutral Agent Runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ai_os.tasks import ReviewResult, Task, TaskStatus


class AgentRole(str, Enum):
    CONTROLLER = "Controller"
    PLANNER = "Planner"
    RESEARCHER = "Researcher"
    DEVELOPER = "Developer"
    TESTER = "Tester"
    REVIEWER = "Reviewer"
    FIXER = "Fixer"


class Capability(str, Enum):
    GOVERN = "govern"
    PLAN = "plan"
    RESEARCH = "research"
    IMPLEMENT = "implement"
    TEST = "test"
    REVIEW = "review"
    FIX = "fix"


class Permission(str, Enum):
    READ_CONTROL = "read_control"
    PROPOSE_CHANGE = "propose_change"
    MODIFY_CODE = "modify_code"
    MODIFY_CONTROL = "modify_control"
    UPDATE_TASK_STATUS = "update_task_status"
    COORDINATE = "coordinate"
    APPROVE_REVIEW = "approve_review"
    COMPLETE_TASK = "complete_task"


class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


@dataclass(frozen=True)
class AgentDescriptor:
    role: AgentRole
    capabilities: frozenset[Capability]
    permissions: frozenset[Permission]
    description: str


@dataclass(frozen=True)
class ExecutionRequest:
    task: Task
    capability: Capability
    objective: str
    actor: str
    requested_role: AgentRole | None = None
    required_permission: Permission | None = None
    target_status: TaskStatus | None = None
    review_result: ReviewResult | None = None
    evidence: tuple[str, ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Handoff:
    task_id: str
    state: TaskStatus
    objective: str
    completed: tuple[str, ...]
    artifacts: tuple[str, ...]
    tests: tuple[str, ...]
    risks: tuple[str, ...]
    remaining: tuple[str, ...]
    next_action: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionResult:
    task_id: str
    role: AgentRole
    capability: Capability
    status: ExecutionStatus
    summary: str
    handoff: Handoff
    review_result: ReviewResult | None = None
    findings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
