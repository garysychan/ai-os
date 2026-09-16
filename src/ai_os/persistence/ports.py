"""Typed persistence ports implemented by runtime stores."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from ai_os.adapters import AdapterAuditEvent
from ai_os.controller import ControllerSession
from ai_os.execution import ExecutionPlan, ExecutionSession

from .models import PruneResult, StoreStatus


class ControllerSessionRepository(Protocol):
    def save_controller_session(self, session: ControllerSession) -> None: ...

    def get_controller_session(self, session_id: str) -> ControllerSession: ...


class ExecutionRepository(Protocol):
    def save_execution_plan(self, plan: ExecutionPlan) -> None: ...

    def get_execution_plan(self, plan_id: str) -> ExecutionPlan: ...

    def save_execution_session(self, session: ExecutionSession) -> None: ...

    def get_execution_session(self, execution_id: str) -> ExecutionSession: ...


class AdapterAuditRepository(Protocol):
    def append_adapter_audit(self, event: AdapterAuditEvent) -> None: ...

    def list_adapter_audit(
        self, *, invocation_id: str | None = None, limit: int = 100
    ) -> tuple[AdapterAuditEvent, ...]: ...


class RuntimeStore(
    ControllerSessionRepository,
    ExecutionRepository,
    AdapterAuditRepository,
    Protocol,
):
    def initialize(self) -> StoreStatus: ...

    def migrate(self) -> StoreStatus: ...

    def status(self) -> StoreStatus: ...

    def prune(self, *, before: datetime, limit: int = 100) -> PruneResult: ...
