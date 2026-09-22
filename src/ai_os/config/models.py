"""Immutable versioned runtime configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ai_os.secrets.models import SecretReference


class EnvironmentProfile(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    model: str
    api_key: SecretReference
    schema_version: int = 1


@dataclass(frozen=True)
class RuntimeConfig:
    environment: EnvironmentProfile
    database_path: str
    execution_timeout_seconds: int
    scheduler_lease_seconds: int
    audit_retention_days: int
    providers: tuple[ProviderConfig, ...] = ()
    feature_flags: tuple[str, ...] = ()
    schema_version: int = 1

    def redacted(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "environment": self.environment.value,
            "database_path": self.database_path,
            "execution_timeout_seconds": self.execution_timeout_seconds,
            "scheduler_lease_seconds": self.scheduler_lease_seconds,
            "audit_retention_days": self.audit_retention_days,
            "providers": [
                {
                    "name": item.name,
                    "model": item.model,
                    "api_key_ref": item.api_key.redacted,
                }
                for item in self.providers
            ],
            "feature_flags": list(self.feature_flags),
        }
