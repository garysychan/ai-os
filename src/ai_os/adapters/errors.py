"""Adapter Layer errors."""


class AdapterError(Exception):
    """Base Adapter Layer error."""


class AdapterValidationError(AdapterError):
    """Adapter input or output is structurally invalid."""


class AdapterPolicyError(AdapterError):
    """Adapter invocation violates an authority or safety policy."""


class AdapterRegistryError(AdapterError):
    """Adapter registration or resolution failed."""


class AdapterExecutionError(AdapterError):
    """A registered Adapter failed safely."""
