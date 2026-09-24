"""Fail-closed redaction for runtime evidence."""

from __future__ import annotations

import re

from ai_os.controller import ControllerStage
from ai_os.workflows import WorkflowStatus

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
_SAFE_CORRELATION_PATTERNS = {
    "attempt": re.compile(r"^[1-9][0-9]{0,8}$"),
    "source_sequence": re.compile(r"^[1-9][0-9]{0,8}$"),
    "method": re.compile(r"^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$"),
    "route": re.compile(r"^/[A-Za-z0-9._{}:/-]{1,199}$"),
    "status_code": re.compile(r"^[1-5][0-9]{2}$"),
    "outcome": re.compile(r"^[A-Z_]{1,32}$"),
    "duration_ms": re.compile(r"^[0-9]{1,9}$"),
}
_SAFE_STAGES = frozenset(
    {stage.value for stage in ControllerStage}
    | {status.value for status in WorkflowStatus}
    | {"AUTHORIZATION"}
)


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
        pattern = _SAFE_CORRELATION_PATTERNS.get(clean_key)
        is_safe = (clean_key == "stage" and value in _SAFE_STAGES) or (
            pattern is not None and pattern.fullmatch(value) is not None
        )
        redacted.append((clean_key, value if is_safe else "[REDACTED]"))
    return tuple(redacted)
