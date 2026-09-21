"""Adapter from fenced Scheduler requests to the existing Workflow authority chain."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime

from ai_os.tasks import Task, TaskStatus
from ai_os.workflows import WorkflowEngine, WorkflowStatus

from .errors import SchedulerValidationError
from .models import DispatchRequest


@dataclass(frozen=True)
class DispatchPolicySnapshot:
    task: Task
    dependency_states: Mapping[str, TaskStatus]
    objective: str
    approval_evidence: tuple[str, ...] = ()


class WorkflowDispatchGateway:
    """Revalidate current policy inputs and delegate only to WorkflowEngine."""

    def __init__(
        self,
        engine: WorkflowEngine,
        policy_snapshot: Callable[[str], DispatchPolicySnapshot],
    ) -> None:
        self.engine = engine
        self.policy_snapshot = policy_snapshot

    def dispatch(
        self,
        request: DispatchRequest,
        *,
        clock: Callable[[], datetime],
        cancelled: Callable[[], bool],
    ) -> bool:
        snapshot = self.policy_snapshot(request.task_id)
        if snapshot.task.task_id != request.task_id:
            raise SchedulerValidationError("dispatch policy returned a mismatched Task")
        if snapshot.task.status not in {TaskStatus.IN_PROGRESS, TaskStatus.REVIEW}:
            raise SchedulerValidationError("Task is not dispatchable at execution time")
        # WorkflowEngine performs dependency, assignment, permission, approval and budget checks.
        result = self.engine.run(
            snapshot.task,
            request.workflow_name,
            request.workflow_version,
            snapshot.objective,
            dependency_states=dict(snapshot.dependency_states),
            clock=clock,
            cancelled=cancelled,
            deadline=request.deadline,
            approval_evidence=snapshot.approval_evidence,
        )
        return result.session.status is WorkflowStatus.COMPLETED
