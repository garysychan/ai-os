"""Immutable domain models for governed execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from ai_os.agents import AgentRole, Capability, Permission


class StepStatus(StrEnum):
    SUCCESS = "SUCCESS"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class ExecutionOutcome(StrEnum):
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


class ExecutionEventType(StrEnum):
    SESSION_STARTED = "SESSION_STARTED"
    STEP_STARTED = "STEP_STARTED"
    STEP_FINISHED = "STEP_FINISHED"
    SESSION_FINISHED = "SESSION_FINISHED"


@dataclass(frozen=True)
class ExecutionStep:
    step_id: str
    adapter: str
    operation: str
    agent_role: AgentRole
    capability: Capability
    required_permission: Permission
    inputs: tuple[tuple[str, str], ...] = ()
    idempotent: bool = False
    max_retries: int = 0


@dataclass(frozen=True)
class ExecutionPlan:
    plan_id: str
    task_id: str
    steps: tuple[ExecutionStep, ...]
    max_steps: int


@dataclass(frozen=True)
class ExecutionContext:
    controller_session_id: str
    objective: str
    approval_evidence: tuple[str, ...] = ()
    deadline: datetime | None = None


@dataclass(frozen=True)
class StepResult:
    step_id: str
    attempt: int
    status: StepStatus
    summary: str
    outputs: tuple[tuple[str, str], ...] = ()
    evidence: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecutionEvent:
    sequence: int
    execution_id: str
    task_id: str
    event_type: ExecutionEventType
    timestamp: datetime
    reason: str
    step_id: str | None = None
    attempt: int | None = None
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecutionSession:
    execution_id: str
    plan_id: str
    task_id: str
    controller_session_id: str
    started_at: datetime
    updated_at: datetime
    events: tuple[ExecutionEvent, ...]
    results: tuple[StepResult, ...] = ()
    outcome: ExecutionOutcome | None = None
    blocking_findings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecutionResult:
    execution_id: str
    task_id: str
    outcome: ExecutionOutcome
    step_results: tuple[StepResult, ...]
    evidence: tuple[str, ...]
    findings: tuple[str, ...] = ()
