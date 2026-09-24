"""Immutable canonical runtime evidence models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from ai_os.agents import AgentRole, Permission


class RuntimeEventType(StrEnum):
    ACCEPTED = "ACCEPTED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    DENIED = "DENIED"
    TIMED_OUT = "TIMED_OUT"


class RuntimeEventSource(StrEnum):
    API = "API"
    CONTROLLER = "CONTROLLER"
    EXECUTION = "EXECUTION"
    ADAPTER = "ADAPTER"
    TOOL = "TOOL"
    WORKFLOW = "WORKFLOW"
    GOVERNANCE = "GOVERNANCE"
    SCHEDULER = "SCHEDULER"


@dataclass(frozen=True)
class RuntimeEvent:
    """Versioned, redacted evidence shared across runtime boundaries."""

    event_id: str
    sequence: int
    timestamp: datetime
    event_type: RuntimeEventType
    source: RuntimeEventSource
    task_id: str
    trace_id: str
    summary: str
    schema_version: int = 1
    session_id: str | None = None
    workflow_session_id: str | None = None
    execution_id: str | None = None
    invocation_id: str | None = None
    agent_role: str | None = None
    correlation: tuple[tuple[str, str], ...] = ()
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeEventFilter:
    task_id: str | None = None
    trace_id: str | None = None
    execution_id: str | None = None
    invocation_id: str | None = None
    event_type: RuntimeEventType | None = None
    source: RuntimeEventSource | None = None


@dataclass(frozen=True)
class AuditQueryContext:
    actor_role: AgentRole
    permission: Permission
