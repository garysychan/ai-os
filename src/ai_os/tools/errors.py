"""Errors raised by the governed Tool Registry."""


class ToolError(Exception):
    """Base error for Tool Registry failures."""


class ToolRegistryError(ToolError):
    """Raised when registration or resolution fails closed."""


class ToolPolicyError(ToolError):
    """Raised when an invocation is not authorized."""


class ToolValidationError(ToolError):
    """Raised when Tool data violates the canonical schema."""
