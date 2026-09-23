"""Canonical authentication models."""

from __future__ import annotations

from dataclasses import dataclass

from ai_os.agents import AgentRole


@dataclass(frozen=True)
class Principal:
    principal_id: str
    role: AgentRole
    credential_id: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported Principal schema version")
        if not self.principal_id.strip() or not self.credential_id.strip():
            raise ValueError("Principal identifiers must not be empty")


@dataclass(frozen=True)
class CredentialBinding:
    credential_id: str
    token_digest: str
    principal_id: str
    role: AgentRole

    def __post_init__(self) -> None:
        if not self.credential_id.strip() or not self.principal_id.strip():
            raise ValueError("credential binding identifiers must not be empty")
        if len(self.token_digest) != 64 or any(
            character not in "0123456789abcdef" for character in self.token_digest
        ):
            raise ValueError("credential token digest must be canonical SHA-256 hex")
