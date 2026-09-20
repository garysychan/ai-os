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
_SENSITIVE_PATTERN = re.compile(
    r"(?i)(authorization|bearer|credential|password|secret|token|api[_-]?key|"
    r"prompt|provider[_-]?payload|private[_-]?key)"
)


def sensitive_key(value: str) -> bool:
    folded = value.casefold().replace("-", "_")
    return any(key in folded for key in _KEYS)


def redact_text(value: str) -> str:
    if not isinstance(value, str):
        raise ObservabilityValidationError("runtime evidence must be text")
    return "[REDACTED]" if _SENSITIVE_PATTERN.search(value) else value


def redact_pairs(values: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    redacted: list[tuple[str, str]] = []
    for key, value in values:
        clean_key = key.strip()
        if not clean_key:
            raise ObservabilityValidationError("correlation keys must not be empty")
        redacted.append(
            (clean_key, "[REDACTED]" if sensitive_key(clean_key) else redact_text(value))
        )
    return tuple(redacted)
