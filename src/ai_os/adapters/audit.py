"""Redacted immutable Adapter audit evidence."""

from datetime import datetime

from .models import AdapterAuditEvent, AdapterInvocation, AdapterResult

_SENSITIVE = ("authorization", "credential", "password", "secret", "token")


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
    return AdapterAuditEvent(
        sequence=sequence,
        invocation_id=invocation.invocation_id,
        task_id=invocation.task_id,
        adapter=invocation.adapter,
        operation=invocation.operation,
        timestamp=timestamp,
        status=result.status,
        evidence=evidence + result.evidence,
    )
