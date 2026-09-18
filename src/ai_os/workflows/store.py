"""Workflow session persistence boundary and safe local implementations."""

import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from .errors import WorkflowValidationError
from .models import WorkflowEvent, WorkflowSession, WorkflowStatus


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


class JsonWorkflowStore:
    """Persist one immutable session document per hashed session identifier."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory.expanduser().resolve()

    def save(self, session: WorkflowSession) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self._path(session.session_id)
        temporary = target.with_suffix(f".{uuid4().hex}.tmp")
        try:
            temporary.write_text(
                json.dumps(_session_payload(session), indent=2, sort_keys=True),
                encoding="utf-8",
            )
            temporary.replace(target)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise WorkflowValidationError(f"cannot persist Workflow session: {error}") from error

    def get(self, session_id: str) -> WorkflowSession:
        path = self._path(session_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            session = _session_from_payload(payload)
        except FileNotFoundError as error:
            raise WorkflowValidationError(f"unknown Workflow session: {session_id}") from error
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            raise WorkflowValidationError(f"corrupt Workflow session: {session_id}") from error
        if session.session_id != session_id:
            raise WorkflowValidationError("Workflow session identity does not match store key")
        return session

    def _path(self, session_id: str) -> Path:
        digest = sha256(session_id.encode("utf-8")).hexdigest()
        return self.directory / f"{digest}.json"


def _session_payload(session: WorkflowSession) -> dict[str, object]:
    return {
        "session_id": session.session_id,
        "task_id": session.task_id,
        "workflow": session.workflow,
        "workflow_version": session.workflow_version,
        "objective": session.objective,
        "status": session.status.value,
        "started_at": session.started_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "deadline": session.deadline.isoformat() if session.deadline else None,
        "max_steps": session.max_steps,
        "max_fix_attempts": session.max_fix_attempts,
        "approval_evidence": list(session.approval_evidence),
        "controller_session_id": session.controller_session_id,
        "definition_fingerprint": session.definition_fingerprint,
        "events": [
            {
                "sequence": event.sequence,
                "session_id": event.session_id,
                "task_id": event.task_id,
                "event_type": event.event_type,
                "stage": event.stage,
                "timestamp": event.timestamp.isoformat(),
                "summary": event.summary,
                "evidence": list(event.evidence),
            }
            for event in session.events
        ],
    }


def _session_from_payload(payload: object) -> WorkflowSession:
    if not isinstance(payload, dict):
        raise TypeError("Workflow session document must be an object")
    events_payload = payload["events"]
    if not isinstance(events_payload, list):
        raise TypeError("Workflow session events must be a list")
    if any(not isinstance(item, dict) for item in events_payload):
        raise TypeError("Workflow session event must be an object")
    events = tuple(
        WorkflowEvent(
            sequence=int(item["sequence"]),
            session_id=str(item["session_id"]),
            task_id=str(item["task_id"]),
            event_type=str(item["event_type"]),
            stage=str(item["stage"]),
            timestamp=datetime.fromisoformat(str(item["timestamp"])),
            summary=str(item["summary"]),
            evidence=tuple(str(value) for value in item["evidence"]),
        )
        for item in events_payload
        if isinstance(item, dict)
    )
    deadline = payload["deadline"]
    return WorkflowSession(
        session_id=str(payload["session_id"]),
        task_id=str(payload["task_id"]),
        workflow=str(payload["workflow"]),
        workflow_version=str(payload["workflow_version"]),
        objective=str(payload["objective"]),
        status=WorkflowStatus(str(payload["status"])),
        started_at=datetime.fromisoformat(str(payload["started_at"])),
        updated_at=datetime.fromisoformat(str(payload["updated_at"])),
        deadline=datetime.fromisoformat(str(deadline)) if deadline is not None else None,
        max_steps=int(payload["max_steps"]),
        max_fix_attempts=int(payload["max_fix_attempts"]),
        approval_evidence=tuple(str(value) for value in payload["approval_evidence"]),
        events=events,
        controller_session_id=(
            str(payload["controller_session_id"])
            if payload["controller_session_id"] is not None
            else None
        ),
        definition_fingerprint=str(payload.get("definition_fingerprint", "")),
    )
