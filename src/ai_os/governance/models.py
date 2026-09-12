"""Typed models returned by the Control Plane Loader."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AgentDefinition:
    """A parsed agent role from AGENTS.md."""

    name: str
    responsibilities: tuple[str, ...] = ()
    restrictions: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuleDefinition:
    """A mandatory rule from PROJECT_RULES.md."""

    rule_id: str
    text: str
    category: str


@dataclass(frozen=True)
class WorkflowDefinition:
    """The parsed stages, states and transitions from WORKFLOW.md."""

    stages: tuple[str, ...]
    states: frozenset[str]
    transitions: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class TaskDefinition:
    """A task record parsed from TASKS.md."""

    task_id: str
    title: str
    status: str | None = None
    priority: str | None = None
    agents: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()


@dataclass(frozen=True)
class AuthorityEntry:
    """The authoritative document for one decision domain."""

    domain: str
    document: str


@dataclass(frozen=True)
class ControlPlane:
    """A fully loaded and minimally cross-validated Control Plane."""

    root: Path
    documents: dict[str, str]
    agents: dict[str, AgentDefinition]
    rules: dict[str, RuleDefinition]
    workflow: WorkflowDefinition
    tasks: dict[str, TaskDefinition]
    authority_map: dict[str, AuthorityEntry]
    warnings: tuple[str, ...] = field(default_factory=tuple)
