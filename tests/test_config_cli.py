import json

from ai_os.cli import main


def _configuration(tmp_path):
    path = tmp_path / "runtime.json"
    path.write_text(
        json.dumps(
            {
                "environment": "test",
                "providers": [
                    {"name": "primary", "model": "model-1", "api_key_ref": "env://AI_API_KEY"}
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_config_validate_show_and_dry_run_are_redacted(tmp_path, capsys, monkeypatch) -> None:
    path = _configuration(tmp_path)
    monkeypatch.setenv("AI_API_KEY", "do-not-print-this")
    assert main(["config", "validate", str(path), "--profile", "test", "--json"]) == 0
    assert (
        main(
            ["config", "show", str(path), "--profile", "test", "--actor-role", "Reviewer", "--json"]
        )
        == 0
    )
    assert (
        main(
            [
                "config",
                "resolve",
                str(path),
                "--profile",
                "test",
                "--actor-role",
                "Controller",
                "--dry-run",
                "--json",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "env://AI_API_KEY" in output
    assert "do-not-print-this" not in output


def test_profiles_and_authorized_secret_check(capsys, monkeypatch) -> None:
    monkeypatch.setenv("AI_API_KEY", "do-not-print-this")
    assert main(["config", "profiles", "--json"]) == 0
    assert (
        main(["secrets", "check", "env://AI_API_KEY", "--actor-role", "Controller", "--json"]) == 0
    )
    output = capsys.readouterr().out
    assert "production" in output
    assert "do-not-print-this" not in output


def test_secret_check_rejects_unauthorized_role(capsys) -> None:
    assert main(["secrets", "check", "env://AI_API_KEY", "--actor-role", "Reviewer", "--json"]) == 2
    assert "SecretAuthorizationError" in capsys.readouterr().out
