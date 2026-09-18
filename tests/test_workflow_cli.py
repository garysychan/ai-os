"""CLI tests for Workflow Registry, validation, dry-run and session inspection."""

import json
from pathlib import Path

import pytest

from ai_os.cli import main


def test_workflow_list_and_describe(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["workflow", "list", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["workflows"][0]["name"] == "coding"
    assert main(["workflow", "describe", "coding", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"


def test_workflow_validate_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    definition = {
        "name": "coding-copy",
        "version": "1",
        "description": "validated definition",
        "driver": "controller_lifecycle",
        "max_steps": 1,
        "max_fix_attempts": 0,
        "stages": [
            {
                "name": "implement",
                "agent_role": "Developer",
                "capability": "implement",
                "required_permission": "modify_code",
            }
        ],
    }
    path = tmp_path / "workflow.json"
    path.write_text(json.dumps(definition), encoding="utf-8")
    assert main(["workflow", "validate", str(path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"


def test_workflow_dry_run_and_session(capsys: pytest.CaptureFixture[str]) -> None:
    repository = Path(__file__).parent.parent
    assert (
        main(
            [
                "workflow",
                "dry-run",
                "coding",
                "TASK-0015",
                "--objective",
                "validate architecture",
                "--root",
                str(repository),
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["external_side_effects"] is False
    assert main(["workflow", "session", payload["session_id"], "--json"]) == 0
    inspected = json.loads(capsys.readouterr().out)
    assert inspected["workflow_status"] == "CREATED"


def test_workflow_unknown_name_fails_closed(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["workflow", "describe", "unknown", "--json"]) == 2
    assert "unknown Workflow" in json.loads(capsys.readouterr().out)["error"]
