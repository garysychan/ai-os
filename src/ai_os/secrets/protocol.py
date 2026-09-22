"""Secret provider port without enumeration capability."""

from typing import Protocol

from .models import SecretReference


class SecretProvider(Protocol):
    def resolve(self, reference: SecretReference) -> str | None: ...
