"""Persistent Runtime Store errors."""


class PersistenceError(Exception):
    """Base persistence error."""


class PersistenceConfigurationError(PersistenceError):
    """The database path or store configuration is unsafe."""


class PersistenceMigrationError(PersistenceError):
    """The database schema cannot be safely migrated."""


class PersistenceIntegrityError(PersistenceError):
    """Stored data is corrupt, incompatible, or violates an invariant."""


class PersistenceNotFoundError(PersistenceError):
    """The requested runtime record does not exist."""
