"""Deterministic Adapter model validation."""

from datetime import datetime

from .errors import AdapterValidationError
from .models import AdapterInvocation, AdapterMetadata, AdapterResult


def validate_metadata(metadata: AdapterMetadata) -> None:
    if not metadata.name.strip() or not metadata.version.strip():
        raise AdapterValidationError("adapter name and version must not be empty")
    if not metadata.operations or any(not item.strip() for item in metadata.operations):
        raise AdapterValidationError("adapter operations must not be empty")
    if not metadata.idempotent_operations <= metadata.operations:
        raise AdapterValidationError("idempotent operations must be declared operations")


def validate_invocation(invocation: AdapterInvocation, now: datetime) -> None:
    if now.tzinfo is None or now.utcoffset() is None:
        raise AdapterValidationError("current time must be timezone-aware")
    values = (
        invocation.invocation_id,
        invocation.task_id,
        invocation.adapter,
        invocation.version,
        invocation.operation,
    )
    if any(not value.strip() for value in values):
        raise AdapterValidationError("invocation identifiers must not be empty")
    if invocation.attempt <= 0:
        raise AdapterValidationError("attempt must be positive")
    if invocation.max_attempts <= 0:
        raise AdapterValidationError("max_attempts must be positive")
    if invocation.attempt > invocation.max_attempts:
        raise AdapterValidationError("attempt exceeds finite attempt limit")
    if len(dict(invocation.inputs)) != len(invocation.inputs):
        raise AdapterValidationError("input keys must be unique")
    if invocation.deadline is not None:
        if invocation.deadline.tzinfo is None or invocation.deadline.utcoffset() is None:
            raise AdapterValidationError("deadline must be timezone-aware")
        if now >= invocation.deadline:
            raise AdapterValidationError("invocation deadline has expired")


def validate_result(result: AdapterResult, invocation: AdapterInvocation, max_output: int) -> None:
    if result.invocation_id != invocation.invocation_id:
        raise AdapterValidationError("result invocation_id does not match invocation")
    size = sum(len(key.encode()) + len(value.encode()) for key, value in result.outputs)
    if size > max_output:
        raise AdapterValidationError("adapter result exceeds output limit")
