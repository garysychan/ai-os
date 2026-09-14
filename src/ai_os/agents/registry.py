"""Deterministic registry of executable Agents."""

from __future__ import annotations

from collections.abc import Iterable

from .base import Agent
from .errors import AgentNotFoundError, AgentValidationError, DuplicateAgentError
from .models import AgentRole


class AgentRegistry:
    def __init__(self, agents: Iterable[Agent] = ()) -> None:
        self._agents: dict[AgentRole, Agent] = {}
        for agent in agents:
            self.register(agent)

    def register(self, agent: Agent) -> None:
        descriptor = agent.descriptor
        if not descriptor.capabilities:
            raise AgentValidationError(
                f"{descriptor.role.value} must declare at least one capability"
            )
        if not descriptor.supported_statuses:
            raise AgentValidationError(
                f"{descriptor.role.value} must declare supported task states"
            )
        if descriptor.role in self._agents:
            raise DuplicateAgentError(
                f"Agent already registered: {descriptor.role.value}"
            )
        self._agents[descriptor.role] = agent

    def get(self, role: AgentRole) -> Agent:
        try:
            return self._agents[role]
        except KeyError as error:
            raise AgentNotFoundError(
                f"No Agent registered for role: {role.value}"
            ) from error

    def list(self) -> tuple[Agent, ...]:
        return tuple(
            self._agents[role]
            for role in sorted(self._agents, key=lambda item: item.value)
        )
