"""Typed, provider-neutral execution port contracts."""

from __future__ import annotations

from typing import Protocol

from .models import ExecutionContext, ExecutionStep, StepResult, StepStatus


class ExecutionAdapter(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def operations(self) -> frozenset[str]: ...

    @property
    def has_external_side_effects(self) -> bool: ...

    def execute(
        self, step: ExecutionStep, context: ExecutionContext, attempt: int
    ) -> StepResult: ...


class NoOpAdapter:
    """Safe adapter for validation, dry-runs, and tests."""

    def __init__(self, name: str, operations: frozenset[str]) -> None:
        self._name = name.strip()
        self._operations = operations

    @property
    def name(self) -> str:
        return self._name

    @property
    def operations(self) -> frozenset[str]:
        return self._operations

    @property
    def has_external_side_effects(self) -> bool:
        return False

    def execute(self, step: ExecutionStep, context: ExecutionContext, attempt: int) -> StepResult:
        return StepResult(
            step_id=step.step_id,
            attempt=attempt,
            status=StepStatus.SUCCESS,
            summary=f"dry-run: {self.name}.{step.operation}",
            outputs=step.inputs,
            evidence=("no-op adapter; no external side effect",),
        )
