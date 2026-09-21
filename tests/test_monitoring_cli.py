from __future__ import annotations

import json

from ai_os.cli import main


def test_health_cli_reports_unavailable_for_empty_store(tmp_path, capsys) -> None:
    database = tmp_path / "runtime.db"
    assert main(["store", "init", "--database", str(database), "--json"]) == 0
    capsys.readouterr()

    code = main(
        [
            "health",
            "--database",
            str(database),
            "--actor-role",
            "Reviewer",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["health"] == "UNAVAILABLE"


def test_metrics_cli_rejects_unbounded_window(tmp_path, capsys) -> None:
    database = tmp_path / "runtime.db"
    assert main(["store", "init", "--database", str(database), "--json"]) == 0
    capsys.readouterr()

    code = main(
        [
            "metrics",
            "--database",
            str(database),
            "--actor-role",
            "Reviewer",
            "--window-seconds",
            "604801",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["error_type"] == "MonitoringValidationError"


def test_health_cli_has_human_readable_output(tmp_path, capsys) -> None:
    database = tmp_path / "runtime.db"
    assert main(["store", "init", "--database", str(database), "--json"]) == 0
    capsys.readouterr()

    assert (
        main(
            [
                "health",
                "--database",
                str(database),
                "--actor-role",
                "Reviewer",
            ]
        )
        == 0
    )

    output = capsys.readouterr().out
    assert output.startswith("RUNTIME HEALTH\n")
    assert not output.startswith("{")
