"""Read-only File Adapter constrained to approved roots."""

from __future__ import annotations

from pathlib import Path

from .errors import AdapterExecutionError, AdapterPolicyError, AdapterValidationError
from .models import (
    AdapterInvocation,
    AdapterMetadata,
    AdapterResult,
    AdapterRisk,
    AdapterStatus,
    SideEffect,
)

_DENIED_NAMES = {".env", ".git-credentials", "id_dsa", "id_ed25519", "id_rsa"}
_DENIED_SUFFIXES = {".key", ".p12", ".pem"}


class ReadOnlyFileAdapter:
    def __init__(self, approved_roots: tuple[Path, ...], max_bytes: int = 1_000_000) -> None:
        if not approved_roots:
            raise AdapterValidationError("at least one approved root is required")
        if max_bytes <= 0:
            raise AdapterValidationError("max_bytes must be positive")
        self._roots = tuple(root.resolve(strict=True) for root in approved_roots)
        if any(not root.is_dir() for root in self._roots):
            raise AdapterValidationError("approved roots must be directories")
        self.max_bytes = max_bytes
        self._metadata = AdapterMetadata(
            name="file-read",
            version="1",
            operations=frozenset({"read_text"}),
            risk=AdapterRisk.LOW,
            side_effect=SideEffect.READ_EXTERNAL,
            idempotent_operations=frozenset({"read_text"}),
        )

    @property
    def metadata(self) -> AdapterMetadata:
        return self._metadata

    def invoke(self, invocation: AdapterInvocation) -> AdapterResult:
        inputs = invocation.input_map()
        raw_path = inputs.get("path", "")
        if not raw_path:
            raise AdapterValidationError("path input is required")
        requested = Path(raw_path)
        if not requested.is_absolute():
            raise AdapterPolicyError("file path must be absolute")
        candidate = requested.resolve(strict=True)
        if not any(candidate.is_relative_to(root) for root in self._roots):
            raise AdapterPolicyError("file path escapes approved roots")
        if (
            candidate.name.casefold() in _DENIED_NAMES
            or candidate.suffix.casefold() in _DENIED_SUFFIXES
        ):
            raise AdapterPolicyError("sensitive file access is denied")
        if not candidate.is_file():
            raise AdapterPolicyError("requested path is not a regular file")
        if candidate.stat().st_size > self.max_bytes:
            raise AdapterPolicyError("file exceeds configured size limit")
        try:
            content = candidate.read_text(encoding=inputs.get("encoding", "utf-8"))
        except (OSError, UnicodeError, LookupError) as error:
            raise AdapterExecutionError("file could not be read safely") from error
        return AdapterResult(
            invocation_id=invocation.invocation_id,
            status=AdapterStatus.SUCCESS,
            summary="read-only file operation completed",
            outputs=(("content", content), ("path", str(candidate))),
            evidence=(f"bytes={candidate.stat().st_size}",),
        )
