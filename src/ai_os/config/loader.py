"""Deterministic JSON and mapping configuration loader."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from ai_os.secrets import SecretError, SecretReference

from .errors import ConfigurationNotFoundError, ConfigurationValidationError
from .models import EnvironmentProfile, ProviderConfig, RuntimeConfig
from .profiles import PROFILE_DEFAULTS
from .validation import validate_config

_KEYS = frozenset(
    {
        "schema_version",
        "environment",
        "database_path",
        "execution_timeout_seconds",
        "scheduler_lease_seconds",
        "audit_retention_days",
        "providers",
        "feature_flags",
    }
)
_PROVIDER_KEYS = frozenset({"schema_version", "name", "model", "api_key_ref"})


def load_config(
    values: Mapping[str, object] | None = None,
    *,
    profile: EnvironmentProfile = EnvironmentProfile.DEVELOPMENT,
    overrides: Mapping[str, object] | None = None,
) -> RuntimeConfig:
    source = dict(values or {})
    unknown = set(source) - _KEYS
    override_values = dict(overrides or {})
    unknown |= set(override_values) - _KEYS
    if unknown:
        raise ConfigurationValidationError(
            "unknown configuration keys: " + ", ".join(sorted(unknown))
        )
    merged: dict[str, object] = {
        "schema_version": 1,
        "environment": profile.value,
        "providers": [],
        "feature_flags": [],
        **PROFILE_DEFAULTS[profile],
        **source,
        **override_values,
    }
    try:
        environment = EnvironmentProfile(str(merged["environment"]))
        if environment is not profile:
            raise ConfigurationValidationError(
                "configuration profile does not match requested profile"
            )
        providers = _providers(merged["providers"])
        config = RuntimeConfig(
            environment=environment,
            database_path=str(merged["database_path"]),
            execution_timeout_seconds=_integer(merged["execution_timeout_seconds"]),
            scheduler_lease_seconds=_integer(merged["scheduler_lease_seconds"]),
            audit_retention_days=_integer(merged["audit_retention_days"]),
            providers=providers,
            feature_flags=_strings(merged["feature_flags"], "feature_flags"),
            schema_version=_integer(merged["schema_version"]),
        )
    except (KeyError, SecretError, TypeError, ValueError) as error:
        raise ConfigurationValidationError("configuration values are malformed") from error
    validate_config(config)
    return config


def load_config_file(path: str | Path, *, profile: EnvironmentProfile) -> RuntimeConfig:
    source = Path(path)
    if not source.is_file():
        raise ConfigurationNotFoundError(f"configuration file does not exist: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConfigurationValidationError("configuration file is not valid JSON") from error
    if not isinstance(payload, dict):
        raise ConfigurationValidationError("configuration root must be an object")
    return load_config(payload, profile=profile)


def _providers(value: object) -> tuple[ProviderConfig, ...]:
    if not isinstance(value, list) or len(value) > 16:
        raise ConfigurationValidationError("providers must be a bounded list")
    providers: list[ProviderConfig] = []
    for entry in value:
        if not isinstance(entry, dict) or set(entry) - _PROVIDER_KEYS:
            raise ConfigurationValidationError("provider contains unknown fields")
        providers.append(
            ProviderConfig(
                name=str(entry["name"]),
                model=str(entry["model"]),
                api_key=SecretReference.parse(str(entry["api_key_ref"])),
                schema_version=_integer(entry.get("schema_version", 1)),
            )
        )
    return tuple(providers)


def _integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationValidationError("integer configuration value is invalid")
    return value


def _strings(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ConfigurationValidationError(f"{name} must contain non-empty strings")
    return tuple(value)
