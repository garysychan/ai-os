"""Safe versioned defaults for canonical runtime profiles."""

from .models import EnvironmentProfile

PROFILE_DEFAULTS: dict[EnvironmentProfile, dict[str, object]] = {
    EnvironmentProfile.DEVELOPMENT: {
        "database_path": ".ai-os/runtime-dev.db",
        "execution_timeout_seconds": 300,
        "scheduler_lease_seconds": 60,
        "audit_retention_days": 14,
    },
    EnvironmentProfile.TEST: {
        "database_path": ":memory:",
        "execution_timeout_seconds": 30,
        "scheduler_lease_seconds": 10,
        "audit_retention_days": 1,
    },
    EnvironmentProfile.PRODUCTION: {
        "database_path": ".ai-os/runtime.db",
        "execution_timeout_seconds": 300,
        "scheduler_lease_seconds": 60,
        "audit_retention_days": 90,
    },
}
