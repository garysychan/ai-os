"""Bounded redaction before secret-adjacent text crosses a persistence boundary."""

from __future__ import annotations

import re
from collections.abc import Iterable

_AUTHORIZATION_HEADER = re.compile(r"(?im)\b(authorization|proxy-authorization)\s*[:=]\s*[^\r\n]*")
_API_KEY_HEADER = re.compile(r"(?i)\b(x-api-key|api-key)\s*[:=]\s*([^\s,;]+)")
_ASSIGNMENT = re.compile(r"(?i)\b(api[_-]?key|token|password|secret)\s*[:=]\s*([^\s,;]+)")


def redact_text(value: str, *, secret_values: Iterable[str] = ()) -> str:
    redacted = _AUTHORIZATION_HEADER.sub(lambda match: f"{match.group(1)}: [REDACTED]", value)
    redacted = _API_KEY_HEADER.sub(lambda match: f"{match.group(1)}: [REDACTED]", redacted)
    redacted = _ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", redacted)
    for secret in sorted({item for item in secret_values if item}, key=len, reverse=True):
        redacted = redacted.replace(secret, "[REDACTED]")
    return redacted
