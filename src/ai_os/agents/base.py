"""Common executable Agent contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .models import AgentDescriptor, ExecutionRequest, ExecutionResult


class Agent(ABC):
    """Provider-neutral Agent interface."""

    @property
    @abstractmethod
    def descriptor(self) -> AgentDescriptor:
        """Return immutable identity, capability, and permission metadata."""

    @abstractmethod
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute one validated request without mutating its Task."""
