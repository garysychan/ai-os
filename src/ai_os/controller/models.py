"""Immutable Controller orchestration domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ai_os.agents import AgentRole, ExecutionResult
from ai_os.tasks import TaskStatus
from ai_os.workflow import TransitionEvent


class ControllerStage(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    TESTING = "TESTING"
    REVIEWING = "REVIEWING"
    FIXING = "FIXING"
    TERMINAL = "TERMINAL"


class ControllerOutcome(str, Enum):
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


class ControllerEventType(str, Enum):
    SESSION_STARTED = "SESSION_STARTED"
    AGENT_DISPATCHED = "AGENT_DISPATCHED"
    RESULT_RECORDED = "RESULT_RECORDED"
    TASK_TRANSITIONED = "TASK_TRANSITIONED"
    SESSION_TERMINATED = "SESSION_TERMINATED"


@dataclass(frozen=True)
class TraceEvent:
    sequence: int
    session_id: str
    task_id: str
    event_type: ControllerEventType
    stage: ControllerStage
    actor: AgentRole
    timestamp: datetime
    reason: str
    evidence: tuple[str, ...] = ()
    correlation: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ControllerSession:
    session_id: str
    task_id: str
    objective: str
    stage: ControllerStage
    task_status: TaskStatus
    started_at: datetime
    updated_at: datetime
    max_fix_attempts: int
    fix_attempts: int = 0
    approval_evidence: tuple[str, ...] = ()
    events: tuple[TraceEvent, ...] = ()
    results: tuple[ExecutionResult, ...] = ()
    transitions: tuple[TransitionEvent, ...] = ()
    blocking_findings: tuple[str, ...] = ()
    outcome: ControllerOutcome | None = None
