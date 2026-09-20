"""Validation and construction for canonical runtime events."""

from __future__ import annotations

from dataclasses import replace

from .errors import ObservabilityValidationError
from .models import RuntimeEvent
from .redaction import redact_pairs, redact_text

_IDENTIFIERS = (
    "event_id",
    "task_id",
    "trace_id",
    "session_id",
    "workflow_session_id",
    "execution_id",
    "invocation_id",
)


def validate_event(event: RuntimeEvent) -> RuntimeEvent:
    if event.schema_version != 1:
        raise ObservabilityValidationError("unsupported runtime event schema version")
    if isinstance(event.sequence, bool) or event.sequence < 1:
        raise ObservabilityValidationError("event sequence must be positive")
    if event.timestamp.tzinfo is None or event.timestamp.utcoffset() is None:
        raise ObservabilityValidationError("event timestamp must be timezone-aware")
    for field in _IDENTIFIERS:
        value = getattr(event, field)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ObservabilityValidationError(f"{field} must not be empty")
    if not event.summary.strip():
        raise ObservabilityValidationError("event summary must not be empty")
    keys = [key for key, _ in event.correlation]
    if len(keys) != len(set(keys)):
        raise ObservabilityValidationError("correlation keys must be unique")
    return event


def sanitize_event(event: RuntimeEvent) -> RuntimeEvent:
    validated = validate_event(event)
    sanitized = replace(
        validated,
        event_id=validated.event_id.strip(),
        task_id=validated.task_id.strip(),
        trace_id=validated.trace_id.strip(),
        summary=redact_text(validated.summary.strip()),
        session_id=_clean_optional(validated.session_id),
        workflow_session_id=_clean_optional(validated.workflow_session_id),
        execution_id=_clean_optional(validated.execution_id),
        invocation_id=_clean_optional(validated.invocation_id),
        agent_role=_clean_optional(validated.agent_role),
        correlation=redact_pairs(validated.correlation),
        evidence=tuple(redact_text(item) for item in validated.evidence),
    )
    return validate_event(sanitized)


def _clean_optional(value: str | None) -> str | None:
    return value.strip() if value is not None else None
