"""Exact-name environment provider; enumeration is intentionally absent."""

from __future__ import annotations

import os
from collections.abc import Mapping

from .errors import SecretReferenceError
from .models import SecretReference


class EnvironmentSecretProvider:
    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        self._environment = environment if environment is not None else os.environ

    def resolve(self, reference: SecretReference) -> str | None:
        if reference.schema_version != 1 or reference.provider != "env":
            raise SecretReferenceError("unsupported secret provider or schema")
        return self._environment.get(reference.name)
