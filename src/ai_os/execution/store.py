"""Process-local execution session adapter."""

from .errors import ExecutionValidationError
from .models import ExecutionSession


class InMemoryExecutionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, ExecutionSession] = {}

    def save(self, session: ExecutionSession) -> None:
        self._sessions[session.execution_id] = session

    def get(self, execution_id: str) -> ExecutionSession:
        try:
            return self._sessions[execution_id]
        except KeyError as error:
            raise ExecutionValidationError(f"unknown execution session: {execution_id}") from error

    def clear(self) -> None:
        self._sessions.clear()
