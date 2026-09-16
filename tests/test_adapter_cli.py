"""CLI tests for governed Adapter inspection and dry-run."""

import json
from pathlib import Path

import pytest

from ai_os.cli import main


def test_adapter_list_and_describe(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["adapter", "list", "--root", str(tmp_path), "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["adapters"][0]["name"] == "file-read"
    assert listed["adapters"][0]["side_effect"] == "READ_EXTERNAL"

    assert (
        main(
            [
                "adapter",
                "describe",
                "file-read",
                "--root",
                str(tmp_path),
                "--json",
            ]
        )
        == 0
    )
    described = json.loads(capsys.readouterr().out)
    assert described["status"] == "PASS"


def test_adapter_validate_default_denies_unknown_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["adapter", "validate", "unknown", "--root", str(tmp_path), "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAIL"
    assert "unknown adapter" in payload["error"]


def test_adapter_dry_run_reads_without_returning_content(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "input.txt"
    target.write_text("sensitive report", encoding="utf-8")
    assert (
        main(
            [
                "adapter",
                "dry-run",
                "file-read",
                "--root",
                str(tmp_path),
                "--path",
                str(target),
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "PASS"
    assert payload["content_returned"] is False
    assert payload["content_bytes"] == len("sensitive report")
    assert "sensitive report" not in json.dumps(payload)


def test_adapter_dry_run_denies_escape(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    approved = tmp_path / "approved"
    approved.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    assert (
        main(
            [
                "adapter",
                "dry-run",
                "file-read",
                "--root",
                str(approved),
                "--path",
                str(outside),
                "--json",
            ]
        )
        == 2
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAIL"
    assert "escapes approved roots" in payload["error"]
