"""Fail-closed configuration validation."""

from pathlib import PurePosixPath, PureWindowsPath

from ai_os.secrets import SecretError, SecretReference

from .errors import ConfigurationValidationError
from .models import EnvironmentProfile, RuntimeConfig


def validate_config(config: RuntimeConfig) -> None:
    if config.schema_version != 1:
        raise ConfigurationValidationError("unsupported configuration schema version")
    if not config.database_path or "\x00" in config.database_path:
        raise ConfigurationValidationError("database path is invalid")
    if config.environment is EnvironmentProfile.PRODUCTION and config.database_path == ":memory:":
        raise ConfigurationValidationError("production cannot use an in-memory database")
    posix_path = PurePosixPath(config.database_path)
    windows_path = PureWindowsPath(config.database_path)
    if (
        posix_path.is_absolute()
        or windows_path.drive
        or windows_path.root
        or ".." in posix_path.parts
        or ".." in windows_path.parts
    ):
        raise ConfigurationValidationError("database path must remain repository-relative")
    if not 1 <= config.execution_timeout_seconds <= 86_400:
        raise ConfigurationValidationError("execution timeout is outside configured bounds")
    if not 5 <= config.scheduler_lease_seconds <= 300:
        raise ConfigurationValidationError("scheduler lease is outside configured bounds")
    if not 1 <= config.audit_retention_days <= 3_650:
        raise ConfigurationValidationError("audit retention is outside configured bounds")
    names: set[str] = set()
    for provider in config.providers:
        if provider.schema_version != 1 or not provider.name or not provider.model:
            raise ConfigurationValidationError("provider configuration is invalid")
        if provider.name in names:
            raise ConfigurationValidationError(f"duplicate provider name: {provider.name}")
        try:
            canonical_reference = SecretReference.parse(provider.api_key.redacted)
        except SecretError as error:
            raise ConfigurationValidationError("provider secret reference is invalid") from error
        if canonical_reference != provider.api_key:
            raise ConfigurationValidationError("provider secret reference is not canonical")
        names.add(provider.name)
    if len(config.feature_flags) > 64 or len(set(config.feature_flags)) != len(
        config.feature_flags
    ):
        raise ConfigurationValidationError("feature flags are duplicated or excessive")
