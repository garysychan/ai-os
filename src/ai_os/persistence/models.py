"""Immutable persistence configuration and status models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoreConfig:
    database: Path
    denied_paths: tuple[Path, ...] = ()
    busy_timeout_ms: int = 5_000
    max_query_limit: int = 1_000


@dataclass(frozen=True)
class StoreStatus:
    database: Path
    initialized: bool
    schema_version: int
    current_schema_version: int
    controller_sessions: int
    execution_plans: int
    execution_sessions: int
    adapter_audit_events: int


@dataclass(frozen=True)
class PruneResult:
    controller_sessions: int = 0
    execution_plans: int = 0
    execution_sessions: int = 0
    adapter_audit_events: int = 0
