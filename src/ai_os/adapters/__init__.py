"""Governed AI OS V2 Adapter Layer."""

from .audit import make_audit_event, redact_pairs
from .errors import (
    AdapterError,
    AdapterExecutionError,
    AdapterPolicyError,
    AdapterRegistryError,
    AdapterValidationError,
)
from .file_read import ReadOnlyFileAdapter
from .models import (
    AdapterAuditEvent,
    AdapterInvocation,
    AdapterMetadata,
    AdapterResult,
    AdapterRisk,
    AdapterStatus,
    SideEffect,
)
from .policy import AdapterPolicy
from .protocol import Adapter
from .registry import AdapterRegistry
from .service import AdapterService
from .validation import validate_invocation, validate_metadata, validate_result

__all__ = [
    "Adapter",
    "AdapterAuditEvent",
    "AdapterError",
    "AdapterExecutionError",
    "AdapterInvocation",
    "AdapterMetadata",
    "AdapterPolicy",
    "AdapterPolicyError",
    "AdapterRegistry",
    "AdapterRegistryError",
    "AdapterResult",
    "AdapterRisk",
    "AdapterService",
    "AdapterStatus",
    "AdapterValidationError",
    "ReadOnlyFileAdapter",
    "SideEffect",
    "make_audit_event",
    "redact_pairs",
    "validate_invocation",
    "validate_metadata",
    "validate_result",
]
