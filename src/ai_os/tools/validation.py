"""Deterministic validation for Tool Registry models."""

from ai_os.agents.permissions import CAPABILITY_PERMISSION

from .errors import ToolValidationError
from .models import ToolInvocation, ToolMetadata, ToolOperation


def validate_operation(operation: ToolOperation) -> None:
    identifiers = (
        operation.name,
        operation.adapter,
        operation.adapter_version,
        operation.adapter_operation,
    )
    if any(not value.strip() for value in identifiers):
        raise ToolValidationError("Tool operation identifiers must not be empty")
    canonical = CAPABILITY_PERMISSION[operation.capability]
    if operation.required_permission is not canonical:
        raise ToolValidationError(
            f"capability {operation.capability.value} requires {canonical.value}"
        )


def validate_metadata(metadata: ToolMetadata) -> None:
    if not metadata.name.strip() or not metadata.version.strip():
        raise ToolValidationError("Tool name and version must not be empty")
    if not metadata.description.strip():
        raise ToolValidationError("Tool description must not be empty")
    if not metadata.operations:
        raise ToolValidationError("Tool must declare at least one operation")
    names = [item.name for item in metadata.operations]
    if len(names) != len(set(names)):
        raise ToolValidationError("Tool operation names must be unique")
    for operation in metadata.operations:
        validate_operation(operation)


def validate_invocation(invocation: ToolInvocation) -> None:
    identifiers = (
        invocation.invocation_id,
        invocation.task_id,
        invocation.tool,
        invocation.version,
        invocation.operation,
    )
    if any(not value.strip() for value in identifiers):
        raise ToolValidationError("Tool invocation identifiers must not be empty")
    if invocation.attempt <= 0 or invocation.max_attempts <= 0:
        raise ToolValidationError("Tool invocation attempts must be positive")
    if invocation.attempt > invocation.max_attempts:
        raise ToolValidationError("attempt exceeds finite attempt limit")
    if len(dict(invocation.inputs)) != len(invocation.inputs):
        raise ToolValidationError("Tool input keys must be unique")
