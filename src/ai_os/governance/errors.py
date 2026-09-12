"""Errors raised while loading the AI OS Control Plane."""


class ControlPlaneError(Exception):
    """Base error for Control Plane loading or validation failures."""


class MissingControlPlaneFileError(ControlPlaneError):
    """Raised when one or more required Control Plane files are missing."""


class ControlPlaneParseError(ControlPlaneError):
    """Raised when a required document section cannot be parsed."""
