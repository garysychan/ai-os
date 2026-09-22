import json

import pytest

from ai_os.config import (
    ConfigurationNotFoundError,
    ConfigurationValidationError,
    EnvironmentProfile,
    load_config,
    load_config_file,
    persistence_config,
)


def test_profiles_and_precedence_are_explicit_and_deterministic() -> None:
    config = load_config(
        {"execution_timeout_seconds": 40},
        profile=EnvironmentProfile.TEST,
        overrides={"execution_timeout_seconds": 50},
    )
    assert config.environment is EnvironmentProfile.TEST
    assert config.execution_timeout_seconds == 50
    assert config.scheduler_lease_seconds == 10
    assert str(persistence_config(config).database) == ":memory:"


def test_configuration_contains_only_secret_references() -> None:
    config = load_config(
        {
            "providers": [
                {"name": "primary", "model": "model-1", "api_key_ref": "env://AI_API_KEY"}
            ]
        }
    )
    assert config.providers[0].api_key.redacted == "env://AI_API_KEY"
    assert config.redacted()["providers"] == [
        {"name": "primary", "model": "model-1", "api_key_ref": "env://AI_API_KEY"}
    ]


@pytest.mark.parametrize(
    "values",
    [
        {"unknown": True},
        {"schema_version": 2},
        {"execution_timeout_seconds": 0},
        {"scheduler_lease_seconds": 301},
        {"feature_flags": ["same", "same"]},
        {"providers": [{"name": "x", "model": "m", "api_key_ref": "literal-secret"}]},
    ],
)
def test_invalid_configuration_fails_closed(values: dict[str, object]) -> None:
    with pytest.raises(ConfigurationValidationError):
        load_config(values)


def test_profile_mismatch_and_unsafe_production_storage_fail() -> None:
    with pytest.raises(ConfigurationValidationError):
        load_config({"environment": "production"})
    with pytest.raises(ConfigurationValidationError):
        load_config({"database_path": ":memory:"}, profile=EnvironmentProfile.PRODUCTION)


def test_json_file_loading(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"environment": "test"}), encoding="utf-8")
    assert load_config_file(path, profile=EnvironmentProfile.TEST).environment.value == "test"
    with pytest.raises(ConfigurationNotFoundError):
        load_config_file(tmp_path / "missing.json", profile=EnvironmentProfile.TEST)


def test_malformed_file_fails_closed(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ConfigurationValidationError):
        load_config_file(path, profile=EnvironmentProfile.TEST)
