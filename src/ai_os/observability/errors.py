"""Runtime observability errors."""


class ObservabilityError(Exception):
    """Base error for governed runtime evidence."""


class ObservabilityValidationError(ObservabilityError):
    """Raised when an event or query violates the observability contract."""


class ObservabilityNotFoundError(ObservabilityError):
    """Raised when requested evidence does not exist."""


class ObservabilityAuthorizationError(ObservabilityError):
    """Raised when an audit query lacks explicit read authority."""
