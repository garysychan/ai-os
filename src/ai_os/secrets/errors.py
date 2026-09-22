"""Governed secret resolution failures."""


class SecretError(Exception):
    """Base secret boundary failure."""


class SecretReferenceError(SecretError):
    """Secret reference is malformed or unsupported."""


class SecretNotFoundError(SecretError):
    """A required secret is missing or empty."""


class SecretAuthorizationError(SecretError):
    """Caller lacks authority to resolve secret material."""
