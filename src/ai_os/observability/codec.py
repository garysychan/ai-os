"""Deterministic codec for redacted runtime events."""

from __future__ import annotations

import json
from datetime import datetime

from .errors import ObservabilityValidationError
from .models import RuntimeEvent, RuntimeEventSource, RuntimeEventType
from .validation import sanitize_event, validate_event


def dump_runtime_event(event: RuntimeEvent) -> str:
    item = sanitize_event(event)
    return json.dumps(
        {
            "schema_version": item.schema_version,
            "event_id": item.event_id,
            "sequence": item.sequence,
            "timestamp": item.timestamp.isoformat(),
            "event_type": item.event_type.value,
            "source": item.source.value,
            "task_id": item.task_id,
            "trace_id": item.trace_id,
            "summary": item.summary,
            "session_id": item.session_id,
            "workflow_session_id": item.workflow_session_id,
            "execution_id": item.execution_id,
            "invocation_id": item.invocation_id,
            "agent_role": item.agent_role,
            "correlation": list(item.correlation),
            "evidence": list(item.evidence),
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def load_runtime_event(payload: str) -> RuntimeEvent:
    try:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise TypeError
        timestamp = datetime.fromisoformat(data["timestamp"])
        correlation = tuple(_pair(item) for item in data["correlation"])
        evidence = tuple(_text(item) for item in data["evidence"])
        event = RuntimeEvent(
            schema_version=data["schema_version"],
            event_id=_text(data["event_id"]),
            sequence=data["sequence"],
            timestamp=timestamp,
            event_type=RuntimeEventType(data["event_type"]),
            source=RuntimeEventSource(data["source"]),
            task_id=_text(data["task_id"]),
            trace_id=_text(data["trace_id"]),
            summary=_text(data["summary"]),
            session_id=_optional_text(data["session_id"]),
            workflow_session_id=_optional_text(data["workflow_session_id"]),
            execution_id=_optional_text(data["execution_id"]),
            invocation_id=_optional_text(data["invocation_id"]),
            agent_role=_optional_text(data["agent_role"]),
            correlation=correlation,
            evidence=evidence,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise ObservabilityValidationError("invalid stored runtime event") from error
    return validate_event(event)


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError
    return value


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return _text(value)


def _pair(value: object) -> tuple[str, str]:
    if not isinstance(value, list) or len(value) != 2:
        raise TypeError
    return _text(value[0]), _text(value[1])
