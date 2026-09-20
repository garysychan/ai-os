"""Fail-closed redaction for runtime evidence."""

from __future__ import annotations

import re

from .errors import ObservabilityValidationError

_KEYS = (
    "authorization",
    "bearer",
    "credential",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "prompt",
    "provider_payload",
    "private_key",
)
_SAFE_CORRELATION_KEYS = frozenset(
    {
        "attempt",
        "execution_id",
        "invocation_id",
        "plan_id",
        "session_id",
        "source_sequence",
        "stage",
        "step_id",
        "task_id",
        "trace_id",
        "workflow_session_id",
    }
)
_SAFE_VALUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")


def sensitive_key(value: str) -> bool:
    folded = value.casefold().replace("-", "_")
    return any(key in folded for key in _KEYS)


def redact_text(value: str) -> str:
    if not isinstance(value, str):
        raise ObservabilityValidationError("runtime evidence must be text")
    # Opaque runtime text cannot prove that it is public. Persist no free-form value.
    return "[REDACTED]"


def redact_pairs(values: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    redacted: list[tuple[str, str]] = []
    for key, value in values:
        clean_key = key.strip()
        if not clean_key:
            raise ObservabilityValidationError("correlation keys must not be empty")
        is_safe = clean_key in _SAFE_CORRELATION_KEYS and _SAFE_VALUE.fullmatch(value) is not None
        redacted.append((clean_key, value if is_safe else "[REDACTED]"))
    return tuple(redacted)
