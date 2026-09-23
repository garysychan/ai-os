"""Constant-time static bearer authentication with server-side role mapping."""

from __future__ import annotations

import hashlib
import hmac

from .models import CredentialBinding, Principal


def digest_token(token: str) -> str:
    if not token or len(token) > 4_096:
        raise ValueError("credential has an invalid length")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class StaticBearerAuthenticator:
    def __init__(self, bindings: tuple[CredentialBinding, ...]) -> None:
        if not bindings:
            raise ValueError("at least one credential binding is required")
        identifiers = [item.credential_id for item in bindings]
        digests = [item.token_digest for item in bindings]
        if len(identifiers) != len(set(identifiers)) or len(digests) != len(set(digests)):
            raise ValueError("credential bindings must be unique")
        self._bindings = bindings

    def authenticate(self, token: str) -> Principal | None:
        candidate = digest_token(token)
        match: CredentialBinding | None = None
        for binding in self._bindings:
            if hmac.compare_digest(candidate, binding.token_digest):
                match = binding
        if match is None:
            return None
        return Principal(match.principal_id, match.role, match.credential_id)
