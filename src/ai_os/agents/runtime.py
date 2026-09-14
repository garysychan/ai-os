"""Permission-aware orchestration over Task, Registry, Router and Agents."""

from __future__ import annotations

from ai_os.tasks import ReviewResult, TaskStatus, validate_task

from .errors import (
    AgentValidationError,
    ExecutionPreconditionError,
    PermissionDeniedError,
)
from .models import (
    AgentRole,
    Capability,
    ExecutionRequest,
    ExecutionResult,
    Permission,
)
from .permissions import PermissionPolicy
from .router import AgentRouter


class AgentRuntime:
    """Validate and dispatch requests without hidden Task state mutation."""

    def __init__(
        self,
        router: AgentRouter,
        policy: PermissionPolicy | None = None,
    ) -> None:
        self.router = router
        self.policy = policy or router.policy

    def execute(
        self,
        request: ExecutionRequest,
        *,
        dependency_states: dict[str, TaskStatus] | None = None,
    ) -> ExecutionResult:
        validate_task(request.task)
        self._validate_request(request, dependency_states or {})
        agent = self.router.route(request)
        if (
            agent.descriptor.role is not AgentRole.CONTROLLER
            and agent.descriptor.role.value not in request.task.agents
        ):
            raise ExecutionPreconditionError(
                f"{agent.descriptor.role.value} is not assigned to "
                f"{request.task.task_id}"
            )
        if request.task.status not in agent.descriptor.supported_statuses:
            raise ExecutionPreconditionError(
                f"{agent.descriptor.role.value} does not support task state "
                f"{request.task.status.value}"
            )
        self._validate_authority(agent.descriptor.role, request)
        result = agent.execute(request)
        self._validate_result(agent.descriptor.role, result)
        return result

    def _validate_request(
        self,
        request: ExecutionRequest,
        dependency_states: dict[str, TaskStatus],
    ) -> None:
        if not request.objective.strip():
            raise AgentValidationError("execution objective must not be empty")
        if not request.actor.strip():
            raise AgentValidationError("execution actor must not be empty")
        unfinished = tuple(
            item for item in request.task.dependencies
            if dependency_states.get(item) is not TaskStatus.DONE
        )
        if unfinished:
            raise ExecutionPreconditionError(
                "dependencies are not DONE: " + ", ".join(unfinished)
            )
        if request.task.status in {TaskStatus.TODO, TaskStatus.DONE}:
            raise ExecutionPreconditionError(
                f"Task state is not executable: {request.task.status.value}"
            )
        if (
            request.capability is Capability.REVIEW
            and request.task.status is not TaskStatus.REVIEW
        ):
            raise ExecutionPreconditionError(
                "Reviewer execution requires task state REVIEW"
            )
        review_evidence_allowed = (
            request.capability is Capability.REVIEW
            or (
                request.capability is Capability.GOVERN
                and request.target_status is TaskStatus.DONE
            )
        )
        if request.review_result is not None and not review_evidence_allowed:
            raise PermissionDeniedError(
                "Review evidence is only valid for Reviewer execution "
                "or governed completion"
            )

    def _validate_authority(
        self,
        role: AgentRole,
        request: ExecutionRequest,
    ) -> None:
        if request.required_permission is not None:
            self.policy.require(role, request.required_permission)
        if request.target_status is TaskStatus.DONE:
            self.policy.require(role, Permission.COMPLETE_TASK)
            if request.review_result is not ReviewResult.APPROVE:
                raise ExecutionPreconditionError(
                    "DONE requires Reviewer result APPROVE"
                )
        if role in {AgentRole.DEVELOPER, AgentRole.FIXER}:
            if request.target_status is TaskStatus.DONE:
                raise PermissionDeniedError(
                    f"{role.value} cannot complete a Task"
                )

    @staticmethod
    def _validate_result(
        role: AgentRole,
        result: ExecutionResult,
    ) -> None:
        if result.role is not role:
            raise AgentValidationError("Agent result role does not match dispatch")
        if role is not AgentRole.REVIEWER and result.review_result is not None:
            raise PermissionDeniedError(
                "Only Reviewer may emit a review result"
            )
