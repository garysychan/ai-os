"""Runtime configuration failures."""


class ConfigurationError(Exception):
    """Base configuration failure."""


class ConfigurationValidationError(ConfigurationError):
    """Configuration is malformed, unsupported or unsafe."""


class ConfigurationNotFoundError(ConfigurationError):
    """The requested configuration source does not exist."""
