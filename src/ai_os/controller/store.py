"""Explicit in-memory session adapter for CLI inspection and tests."""

from __future__ import annotations

from .errors import ControllerValidationError
from .models import ControllerSession


class InMemorySessionStore:
    """Process-local adapter; it performs no filesystem or network I/O."""

    def __init__(self) -> None:
        self._sessions: dict[str, ControllerSession] = {}

    def save(self, session: ControllerSession) -> None:
        self._sessions[session.session_id] = session

    def get(self, session_id: str) -> ControllerSession:
        try:
            return self._sessions[session_id]
        except KeyError as error:
            raise ControllerValidationError(f"unknown session: {session_id}") from error

    def clear(self) -> None:
        self._sessions.clear()
