"""Persistent Runtime Store CLI tests."""

import json

from ai_os.cli import main
from ai_os.persistence import CURRENT_SCHEMA_VERSION


def test_store_init_status_and_migrate(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "runtime.sqlite"
    for command in ("init", "status", "migrate"):
        assert main(["store", command, "--database", str(database), "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["status"] == "PASS"
        assert payload["initialized"] is True
        assert payload["schema_version"] == CURRENT_SCHEMA_VERSION


def test_store_status_does_not_create_database(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "missing.sqlite"
    assert main(["store", "status", "--database", str(database), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["initialized"] is False
    assert not database.exists()


def test_store_read_only_inspection_reports_missing_record(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    database = tmp_path / "runtime.sqlite"
    assert main(["store", "init", "--database", str(database)]) == 0
    capsys.readouterr()
    assert (
        main(
            [
                "store",
                "session",
                "missing",
                "--database",
                str(database),
                "--json",
            ]
        )
        == 2
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAIL"
    assert payload["error_type"] == "PersistenceNotFoundError"
