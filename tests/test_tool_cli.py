"""CLI tests for governed Tool Registry inspection."""

import json
from pathlib import Path

import pytest

from ai_os.cli import main


def test_tool_list_describe_and_validate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["tool", "list", "--root", str(tmp_path), "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["status"] == "PASS"
    assert listed["tools"][0]["name"] == "file"
    assert listed["tools"][0]["operations"][0]["adapter"] == "file-read@1"

    assert main(["tool", "describe", "file", "--root", str(tmp_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"

    assert main(["tool", "validate", "file", "--root", str(tmp_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"


def test_tool_validate_unknown_fails_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["tool", "validate", "shell", "--root", str(tmp_path), "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "FAIL"
    assert "unknown Tool" in payload["error"]
