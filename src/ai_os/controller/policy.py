"""Authority-preserving Controller orchestration policy."""

from __future__ import annotations

from collections.abc import Mapping

from ai_os.agents import Capability, ExecutionStatus
from ai_os.tasks import Task, TaskStatus, validate_task

from .errors import ControllerPolicyError
from .models import ControllerSession, ControllerStage

_STAGE_BY_CAPABILITY = {
    Capability.GOVERN: ControllerStage.EXECUTING,
    Capability.PLAN: ControllerStage.PLANNING,
    Capability.RESEARCH: ControllerStage.EXECUTING,
    Capability.IMPLEMENT: ControllerStage.EXECUTING,
    Capability.TEST: ControllerStage.TESTING,
    Capability.REVIEW: ControllerStage.REVIEWING,
    Capability.FIX: ControllerStage.FIXING,
}


class ControllerPolicy:
    def validate_start(
        self,
        task: Task,
        objective: str,
        dependency_states: Mapping[str, TaskStatus],
        *,
        max_fix_attempts: int,
    ) -> None:
        validate_task(task)
        if task.status is not TaskStatus.IN_PROGRESS:
            raise ControllerPolicyError("Controller requires an IN_PROGRESS task")
        if not objective.strip():
            raise ControllerPolicyError("Controller objective must not be empty")
        if max_fix_attempts < 0:
            raise ControllerPolicyError("max fix attempts must not be negative")
        unfinished = tuple(
            dependency
            for dependency in task.dependencies
            if dependency_states.get(dependency) is not TaskStatus.DONE
        )
        if unfinished:
            raise ControllerPolicyError("dependencies are not DONE: " + ", ".join(unfinished))

    def stage_for(self, capability: Capability) -> ControllerStage:
        return _STAGE_BY_CAPABILITY[capability]

    def require_dispatchable(self, session: ControllerSession) -> None:
        if session.outcome is not None:
            raise ControllerPolicyError("terminal session cannot dispatch")

    def require_fix_available(self, session: ControllerSession) -> None:
        if session.fix_attempts >= session.max_fix_attempts:
            raise ControllerPolicyError("finite fix limit exhausted")

    @staticmethod
    def result_is_blocking(status: ExecutionStatus) -> bool:
        return status in {
            ExecutionStatus.BLOCKED,
            ExecutionStatus.FAILED,
            ExecutionStatus.ESCALATED,
        }
