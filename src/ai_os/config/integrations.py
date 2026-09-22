"""Typed projections from runtime configuration into component configuration."""

from pathlib import Path

from ai_os.persistence import StoreConfig

from .models import RuntimeConfig
from .validation import validate_config


def persistence_config(config: RuntimeConfig) -> StoreConfig:
    """Construct persistence settings only from a validated runtime model."""
    validate_config(config)
    return StoreConfig(database=Path(config.database_path))
