"""Non-serializing secret references and material."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ai_os.agents import AgentRole, Permission

from .errors import SecretReferenceError

_REFERENCE = re.compile(r"^env://([A-Z][A-Z0-9_]{1,127})$")


@dataclass(frozen=True)
class SecretReference:
    provider: str
    name: str
    schema_version: int = 1

    @classmethod
    def parse(cls, value: str) -> SecretReference:
        match = _REFERENCE.fullmatch(value)
        if match is None:
            raise SecretReferenceError("secret reference must use an approved env:// name")
        return cls("env", match.group(1))

    @property
    def redacted(self) -> str:
        return f"{self.provider}://{self.name}"


@dataclass(frozen=True)
class SecretAccessContext:
    actor_role: AgentRole
    permission: Permission


class SecretMaterial:
    """Opaque secret value whose representation and string conversion stay redacted."""

    __slots__ = ("__value",)

    def __init__(self, value: str) -> None:
        self.__value = value

    def reveal(self) -> str:
        """Return material only after SecretService authorization and resolution."""
        return self.__value

    def __repr__(self) -> str:
        return "SecretMaterial([REDACTED])"

    def __str__(self) -> str:
        return "[REDACTED]"
