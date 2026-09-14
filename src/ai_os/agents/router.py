"""Deterministic, permission-aware Agent routing."""

from __future__ import annotations

from .base import Agent
from .errors import AmbiguousRouteError, RoutingError
from .models import ExecutionRequest
from .permissions import CAPABILITY_PERMISSION, PermissionPolicy
from .registry import AgentRegistry


class AgentRouter:
    def __init__(
        self,
        registry: AgentRegistry,
        policy: PermissionPolicy | None = None,
    ) -> None:
        self.registry = registry
        self.policy = policy or PermissionPolicy()

    def route(self, request: ExecutionRequest) -> Agent:
        if request.requested_role is not None:
            agent = self.registry.get(request.requested_role)
            if request.capability not in agent.descriptor.capabilities:
                raise RoutingError(
                    f"{request.requested_role.value} does not support "
                    f"{request.capability.value}"
                )
            candidates = (agent,)
        else:
            candidates = tuple(
                agent for agent in self.registry.list()
                if request.capability in agent.descriptor.capabilities
            )

        if not candidates:
            raise RoutingError(
                f"No Agent supports capability: {request.capability.value}"
            )
        if len(candidates) > 1:
            roles = ", ".join(agent.descriptor.role.value for agent in candidates)
            raise AmbiguousRouteError(
                f"Ambiguous route for {request.capability.value}: {roles}"
            )

        agent = candidates[0]
        self.policy.require(
            agent.descriptor.role,
            CAPABILITY_PERMISSION[request.capability],
        )
        if request.required_permission is not None:
            self.policy.require(agent.descriptor.role, request.required_permission)
        return agent
