"""Immutable models for governed tools and their Adapter bindings."""

from __future__ import annotations

from dataclasses import dataclass

from ai_os.adapters import AdapterAuditEvent, AdapterResult, AdapterRisk, SideEffect
from ai_os.agents import AgentRole, Capability, Permission


@dataclass(frozen=True)
class ToolOperation:
    """One explicitly governed operation exposed by a Tool."""

    name: str
    capability: Capability
    required_permission: Permission
    risk: AdapterRisk
    side_effect: SideEffect
    idempotent: bool
    approval_required: bool
    adapter: str
    adapter_version: str
    adapter_operation: str


@dataclass(frozen=True)
class ToolMetadata:
    """Versioned Tool identity and its complete operation allow-list."""

    name: str
    version: str
    description: str
    operations: tuple[ToolOperation, ...]


@dataclass(frozen=True)
class ToolInvocation:
    """A request to execute one registered Tool operation."""

    invocation_id: str
    task_id: str
    tool: str
    version: str
    operation: str
    agent_role: AgentRole
    capability: Capability
    required_permission: Permission
    inputs: tuple[tuple[str, str], ...] = ()
    approval_evidence: tuple[str, ...] = ()
    attempt: int = 1
    max_attempts: int = 1


@dataclass(frozen=True)
class ToolResult:
    """Tool-level result preserving the underlying Adapter evidence."""

    tool: str
    version: str
    operation: str
    adapter_result: AdapterResult
    audit: AdapterAuditEvent
