"""Canonical executable role definitions from AGENTS.md."""

from __future__ import annotations

from .base import Agent
from .models import (
    AgentDescriptor,
    AgentRole,
    Capability,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    Handoff,
)
from .permissions import PermissionPolicy

_ROLE_CAPABILITY = {
    AgentRole.CONTROLLER: Capability.GOVERN,
    AgentRole.PLANNER: Capability.PLAN,
    AgentRole.RESEARCHER: Capability.RESEARCH,
    AgentRole.DEVELOPER: Capability.IMPLEMENT,
    AgentRole.TESTER: Capability.TEST,
    AgentRole.REVIEWER: Capability.REVIEW,
    AgentRole.FIXER: Capability.FIX,
}

_ROLE_DESCRIPTION = {
    AgentRole.CONTROLLER: "Coordinates execution and enforces governance gates.",
    AgentRole.PLANNER: "Converts requirements into executable plans.",
    AgentRole.RESEARCHER: "Produces evidence-based research findings.",
    AgentRole.DEVELOPER: "Implements approved, scoped code changes.",
    AgentRole.TESTER: "Validates behavior and acceptance criteria.",
    AgentRole.REVIEWER: "Performs independent quality review.",
    AgentRole.FIXER: "Resolves identified test and review defects.",
}


class CanonicalAgent(Agent):
    """Minimal provider-neutral executor for one canonical role."""

    def __init__(
        self,
        role: AgentRole,
        policy: PermissionPolicy | None = None,
    ) -> None:
        policy = policy or PermissionPolicy()
        self._descriptor = AgentDescriptor(
            role=role,
            capabilities=frozenset({_ROLE_CAPABILITY[role]}),
            permissions=policy.permissions_for(role),
            description=_ROLE_DESCRIPTION[role],
        )

    @property
    def descriptor(self) -> AgentDescriptor:
        return self._descriptor

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        summary = (
            f"{self.descriptor.role.value} accepted "
            f"{request.capability.value}: {request.objective.strip()}"
        )
        handoff = Handoff(
            task_id=request.task.task_id,
            state=request.task.status,
            objective=request.objective.strip(),
            completed=(summary,),
            artifacts=(),
            tests=(),
            risks=(),
            remaining=(),
            next_action="Return result to the Controller",
            evidence=request.evidence,
        )
        return ExecutionResult(
            task_id=request.task.task_id,
            role=self.descriptor.role,
            capability=request.capability,
            status=ExecutionStatus.SUCCESS,
            summary=summary,
            handoff=handoff,
            review_result=request.review_result,
        )


def canonical_agents(
    policy: PermissionPolicy | None = None,
) -> tuple[CanonicalAgent, ...]:
    return tuple(CanonicalAgent(role, policy) for role in AgentRole)
