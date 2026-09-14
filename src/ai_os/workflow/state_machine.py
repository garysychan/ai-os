"""Immutable state transitions and completion-gate enforcement."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone

from ai_os.tasks.models import ReviewResult, Task, TaskStatus
from ai_os.tasks.schema import validate_task

from .errors import (
    CompletionGateError,
    InvalidTransitionError,
    TransitionValidationError,
)
from .transitions import is_valid_transition, normalize_status


@dataclass(frozen=True)
class TransitionContext:
    """Evidence and gate state supplied for one transition."""

    actor: str
    reason: str
    evidence: tuple[str, ...] = ()
    tests_passed: bool | None = None
    review_result: ReviewResult | None = None
    blocking_findings: tuple[str, ...] = ()
    dependency_states: Mapping[str, TaskStatus] = field(default_factory=dict)


@dataclass(frozen=True)
class TransitionEvent:
    """Immutable audit record emitted after a successful transition."""

    task_id: str
    source: TaskStatus
    target: TaskStatus
    actor: str
    reason: str
    timestamp: datetime
    evidence: tuple[str, ...] = ()


def completion_gate_failures(
    task: Task,
    context: TransitionContext,
) -> tuple[str, ...]:
    """Return every reason that prevents a Task from becoming DONE."""
    reasons: list[str] = []

    incomplete = [
        criterion.description
        for criterion in task.acceptance_criteria
        if not criterion.completed
    ]
    if incomplete:
        reasons.append(
            "incomplete acceptance criteria: " + ", ".join(incomplete)
        )
    if context.tests_passed is not True:
        reasons.append("tests have not passed")
    if context.review_result is not ReviewResult.APPROVE:
        reasons.append("Reviewer result is not APPROVE")
    if context.blocking_findings:
        reasons.append(
            "blocking findings remain: "
            + ", ".join(context.blocking_findings)
        )

    unfinished_dependencies = [
        dependency
        for dependency in task.dependencies
        if context.dependency_states.get(dependency) is not TaskStatus.DONE
    ]
    if unfinished_dependencies:
        reasons.append(
            "dependencies are not DONE: "
            + ", ".join(unfinished_dependencies)
        )
    if not context.evidence and not task.completion_evidence:
        reasons.append("completion evidence is missing")

    return tuple(reasons)


class StateMachine:
    """Apply validated state transitions without mutating the input Task."""

    def transition(
        self,
        task: Task,
        target: TaskStatus | str,
        context: TransitionContext,
        *,
        occurred_at: datetime | None = None,
    ) -> tuple[Task, TransitionEvent]:
        """Return an updated Task and audit event, or raise a gate error."""
        validate_task(task)
        normalized_target = normalize_status(target)

        if not context.actor.strip():
            raise TransitionValidationError("transition actor must not be empty")
        if not context.reason.strip():
            raise TransitionValidationError("transition reason must not be empty")
        if not is_valid_transition(task.status, normalized_target):
            raise InvalidTransitionError(
                task.status.value,
                normalized_target.value,
            )

        evidence = tuple(
            dict.fromkeys((*task.completion_evidence, *context.evidence))
        )
        candidate = replace(
            task,
            status=normalized_target,
            completion_evidence=evidence,
        )

        if normalized_target is TaskStatus.DONE:
            failures = completion_gate_failures(candidate, context)
            if failures:
                raise CompletionGateError(failures)

        validate_task(candidate)
        timestamp = occurred_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise TransitionValidationError(
                "transition timestamp must be timezone-aware"
            )

        event = TransitionEvent(
            task_id=task.task_id,
            source=task.status,
            target=normalized_target,
            actor=context.actor.strip(),
            reason=context.reason.strip(),
            timestamp=timestamp,
            evidence=tuple(context.evidence),
        )
        return candidate, event
