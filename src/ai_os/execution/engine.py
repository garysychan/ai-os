"""Deterministic synchronous Execution Engine."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import suppress
from datetime import UTC, datetime

from ai_os.tasks import Task, TaskStatus

from .context import append_event, create_session, finish_session, record_result
from .errors import ExecutionEngineError, ExecutionValidationError
from .models import (
    ExecutionContext,
    ExecutionEvent,
    ExecutionEventType,
    ExecutionOutcome,
    ExecutionPlan,
    ExecutionResult,
    ExecutionSession,
    StepResult,
    StepStatus,
)
from .policy import ExecutionPolicy
from .registry import AdapterRegistry


class ExecutionEngine:
    """Execute finite plans through explicitly registered side-effect-free adapters."""

    def __init__(
        self,
        registry: AdapterRegistry,
        policy: ExecutionPolicy | None = None,
        event_sink: Callable[[ExecutionEvent, str | None, bool], None] | None = None,
        denial_sink: Callable[[str, datetime, str], None] | None = None,
    ) -> None:
        self.registry = registry
        self.policy = policy or ExecutionPolicy()
        self.event_sink = event_sink
        self.denial_sink = denial_sink

    def run(
        self,
        task: Task,
        plan: ExecutionPlan,
        context: ExecutionContext,
        *,
        dependency_states: Mapping[str, TaskStatus],
        clock: Callable[[], datetime] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> tuple[ExecutionSession, ExecutionResult]:
        now = clock or (lambda: datetime.now(UTC))
        is_cancelled = cancelled or (lambda: False)
        started_at = now()
        try:
            self.policy.validate_start(task, plan, context, dependency_states, started_at)
            for step in plan.steps:
                adapter = self.registry.resolve(step.adapter, step.operation)
                self.policy.validate_adapter(adapter)
        except ExecutionEngineError as error:
            self._deny(task.task_id, started_at, type(error).__name__)
            raise

        session = create_session(plan, context, started_at)
        self._emit(session.events[-1], None)
        for step in plan.steps:
            if is_cancelled():
                return self._finish(
                    session, ExecutionOutcome.CANCELLED, now(), "execution cancelled"
                )
            if context.deadline is not None and now() >= context.deadline:
                return self._finish(
                    session,
                    ExecutionOutcome.ESCALATED,
                    now(),
                    "execution deadline exhausted",
                    ("deadline exceeded before next step",),
                )
            adapter = self.registry.resolve(step.adapter, step.operation)
            for attempt in range(1, step.max_retries + 2):
                session = append_event(
                    session,
                    ExecutionEventType.STEP_STARTED,
                    now(),
                    f"execute {step.adapter}.{step.operation}",
                    step_id=step.step_id,
                    attempt=attempt,
                )
                self._emit(session.events[-1], None)
                try:
                    result = adapter.execute(step, context, attempt)
                except Exception as error:
                    result = StepResult(
                        step_id=step.step_id,
                        attempt=attempt,
                        status=StepStatus.FAILED,
                        summary=f"adapter error: {type(error).__name__}",
                        errors=(str(error),),
                    )
                self._validate_result(step.step_id, attempt, result)
                session = record_result(session, result, now())
                self._emit(session.events[-1], result.status.value)
                if result.status is StepStatus.SUCCESS:
                    break
                if result.status is StepStatus.FAILED and attempt <= step.max_retries:
                    continue
                outcome = {
                    StepStatus.BLOCKED: ExecutionOutcome.BLOCKED,
                    StepStatus.FAILED: ExecutionOutcome.FAILED,
                    StepStatus.ESCALATED: ExecutionOutcome.ESCALATED,
                }[result.status]
                findings = result.errors or (result.summary,)
                return self._finish(session, outcome, now(), result.summary, findings)
        return self._finish(session, ExecutionOutcome.COMPLETED, now(), "all steps completed")

    @staticmethod
    def _validate_result(step_id: str, attempt: int, result: StepResult) -> None:
        if result.step_id != step_id or result.attempt != attempt:
            raise ExecutionValidationError("adapter result identity does not match dispatch")
        if not result.summary.strip():
            raise ExecutionValidationError("adapter result summary must not be empty")

    def _finish(
        self,
        session: ExecutionSession,
        outcome: ExecutionOutcome,
        timestamp: datetime,
        reason: str,
        findings: tuple[str, ...] = (),
    ) -> tuple[ExecutionSession, ExecutionResult]:
        terminal = finish_session(session, outcome, timestamp, reason, findings)
        self._emit(
            terminal.events[-1],
            outcome.value,
            timed_out="deadline" in reason.casefold(),
        )
        evidence = tuple(item for result in terminal.results for item in result.evidence)
        return terminal, ExecutionResult(
            execution_id=terminal.execution_id,
            task_id=terminal.task_id,
            outcome=outcome,
            step_results=terminal.results,
            evidence=evidence,
            findings=findings,
        )

    def _emit(self, event: ExecutionEvent, status: str | None, timed_out: bool = False) -> None:
        if self.event_sink is not None:
            with suppress(Exception):
                self.event_sink(event, status, timed_out)

    def _deny(self, task_id: str, timestamp: datetime, reason: str) -> None:
        if self.denial_sink is not None:
            with suppress(Exception):
                self.denial_sink(task_id, timestamp, reason)
