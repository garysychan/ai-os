"""Immutable Adapter Layer domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from ai_os.agents import AgentRole, Capability, Permission


class AdapterRisk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SideEffect(StrEnum):
    NONE = "NONE"
    READ_EXTERNAL = "READ_EXTERNAL"
    WRITE_EXTERNAL = "WRITE_EXTERNAL"


class AdapterStatus(StrEnum):
    SUCCESS = "SUCCESS"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class AdapterMetadata:
    name: str
    version: str
    operations: frozenset[str]
    risk: AdapterRisk
    side_effect: SideEffect
    idempotent_operations: frozenset[str]


@dataclass(frozen=True)
class AdapterInvocation:
    invocation_id: str
    task_id: str
    adapter: str
    version: str
    operation: str
    agent_role: AgentRole
    capability: Capability
    required_permission: Permission
    inputs: tuple[tuple[str, str], ...] = ()
    deadline: datetime | None = None
    attempt: int = 1

    def input_map(self) -> dict[str, str]:
        return dict(self.inputs)


@dataclass(frozen=True)
class AdapterResult:
    invocation_id: str
    status: AdapterStatus
    summary: str
    outputs: tuple[tuple[str, str], ...] = ()
    evidence: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class AdapterAuditEvent:
    sequence: int
    invocation_id: str
    task_id: str
    adapter: str
    operation: str
    timestamp: datetime
    status: AdapterStatus
    evidence: tuple[str, ...] = ()
