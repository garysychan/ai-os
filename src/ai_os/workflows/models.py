"""Immutable domain models for governed Workflow orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from ai_os.agents import AgentRole, Capability, Permission
from ai_os.controller import ControllerSession
from ai_os.tasks import Task


class WorkflowStatus(StrEnum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


TERMINAL_WORKFLOW_STATUSES = frozenset(
    {
        WorkflowStatus.COMPLETED,
        WorkflowStatus.BLOCKED,
        WorkflowStatus.FAILED,
        WorkflowStatus.ESCALATED,
        WorkflowStatus.CANCELLED,
    }
)


@dataclass(frozen=True)
class WorkflowStage:
    name: str
    agent_role: AgentRole
    capability: Capability
    required_permission: Permission


@dataclass(frozen=True)
class WorkflowDefinition:
    name: str
    version: str
    description: str
    driver: str
    stages: tuple[WorkflowStage, ...]
    max_steps: int
    max_fix_attempts: int
    approval_required: bool = False
    required_output_sections: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowEvent:
    sequence: int
    session_id: str
    task_id: str
    event_type: str
    stage: str
    timestamp: datetime
    summary: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowSession:
    session_id: str
    task_id: str
    workflow: str
    workflow_version: str
    objective: str
    status: WorkflowStatus
    started_at: datetime
    updated_at: datetime
    deadline: datetime | None
    max_steps: int
    max_fix_attempts: int
    approval_evidence: tuple[str, ...] = ()
    events: tuple[WorkflowEvent, ...] = ()
    controller_session_id: str | None = None
    definition_fingerprint: str = ""


@dataclass(frozen=True)
class WorkflowResult:
    session: WorkflowSession
    task: Task
    controller_session: ControllerSession
    required_output_sections: tuple[str, ...] = ()
