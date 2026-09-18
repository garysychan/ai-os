"""Explicit in-memory Workflow session store and persistence boundary."""

from typing import Protocol

from .errors import WorkflowValidationError
from .models import WorkflowSession


class WorkflowSessionStore(Protocol):
    def save(self, session: WorkflowSession) -> None: ...

    def get(self, session_id: str) -> WorkflowSession: ...


class InMemoryWorkflowStore:
    def __init__(self) -> None:
        self._sessions: dict[str, WorkflowSession] = {}

    def save(self, session: WorkflowSession) -> None:
        self._sessions[session.session_id] = session

    def get(self, session_id: str) -> WorkflowSession:
        try:
            return self._sessions[session_id]
        except KeyError as error:
            raise WorkflowValidationError(f"unknown Workflow session: {session_id}") from error
