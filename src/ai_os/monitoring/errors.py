"""Runtime monitoring errors."""


class MonitoringError(Exception):
    """Base error for governed monitoring."""


class MonitoringValidationError(MonitoringError):
    """Raised when monitoring input is invalid."""


class MonitoringAuthorizationError(MonitoringError):
    """Raised when a monitoring query is unauthorized."""
