"""Redacted immutable Adapter audit evidence."""

import re
from datetime import datetime

from .models import AdapterAuditEvent, AdapterInvocation, AdapterResult

_SENSITIVE = ("authorization", "credential", "password", "secret", "token")
_SENSITIVE_TEXT = re.compile(
    r"(?i)\b(authorization|credential|password|secret|token)\s*[:=]\s*[^\s,;]+"
)


def redact_text(value: str) -> str:
    return _SENSITIVE_TEXT.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


def redact_pairs(values: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (key, "[REDACTED]" if any(word in key.casefold() for word in _SENSITIVE) else value)
        for key, value in values
    )


def make_audit_event(
    sequence: int,
    invocation: AdapterInvocation,
    result: AdapterResult,
    timestamp: datetime,
) -> AdapterAuditEvent:
    evidence = tuple(f"{key}={value}" for key, value in redact_pairs(invocation.inputs))
    result_evidence = tuple(redact_text(value) for value in result.evidence)
    result_errors = tuple(f"error={redact_text(value)}" for value in result.errors)
    return AdapterAuditEvent(
        sequence=sequence,
        invocation_id=invocation.invocation_id,
        task_id=invocation.task_id,
        adapter=invocation.adapter,
        operation=invocation.operation,
        timestamp=timestamp,
        status=result.status,
        evidence=evidence + result_evidence + result_errors,
    )
