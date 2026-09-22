"""Governed secret provider public API."""

from .environment import EnvironmentSecretProvider
from .errors import (
    SecretAuthorizationError,
    SecretError,
    SecretNotFoundError,
    SecretReferenceError,
)
from .models import SecretAccessContext, SecretMaterial, SecretReference
from .protocol import SecretProvider
from .redaction import redact_text
from .service import SecretService

__all__ = [
    "EnvironmentSecretProvider",
    "SecretAccessContext",
    "SecretAuthorizationError",
    "SecretError",
    "SecretMaterial",
    "SecretNotFoundError",
    "SecretProvider",
    "SecretReference",
    "SecretReferenceError",
    "SecretService",
    "redact_text",
]
