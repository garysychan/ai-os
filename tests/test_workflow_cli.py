"""CLI tests for Workflow Registry, validation, dry-run and session inspection."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from ai_os.cli import main


def test_workflow_list_and_describe(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["workflow", "list", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["workflows"][0]["name"] == "coding"
    assert main(["workflow", "describe", "coding", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"
    assert main(["workflow", "describe", "investment", "--version", "1.0.0", "--json"]) == 0
    described = json.loads(capsys.readouterr().out)["workflows"][0]
    assert described["required_output_sections"] == ["facts", "inference", "assumptions"]


def test_workflow_validate_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    definition = {
        "name": "coding-copy",
        "version": "1",
        "description": "validated definition",
        "driver": "controller_lifecycle",
        "max_steps": 4,
        "max_fix_attempts": 0,
        "stages": [
            {
                "name": "implement",
                "agent_role": "Developer",
                "capability": "implement",
                "required_permission": "modify_code",
            },
            {
                "name": "test",
                "agent_role": "Tester",
                "capability": "test",
                "required_permission": "read_control",
            },
            {
                "name": "review",
                "agent_role": "Reviewer",
                "capability": "review",
                "required_permission": "approve_review",
            },
            {
                "name": "fix",
                "agent_role": "Fixer",
                "capability": "fix",
                "required_permission": "modify_code",
            },
        ],
    }
    path = tmp_path / "workflow.json"
    path.write_text(json.dumps(definition), encoding="utf-8")
    assert main(["workflow", "validate", str(path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"


def test_workflow_dry_run_and_session_across_processes(tmp_path: Path) -> None:
    source = Path(__file__).parent.parent
    repository = tmp_path / "repository"
    repository.mkdir()
    for name in (
        "CONTROL_PLANE.md",
        "AGENTS.md",
        "PROJECT_RULES.md",
        "ARCHITECTURE.md",
        "WORKFLOW.md",
        "TASKS.md",
    ):
        shutil.copy2(source / name, repository / name)
    with (repository / "TASKS.md").open("a", encoding="utf-8") as tasks:
        tasks.write(
            "\n## TASK-9999 — Workflow CLI Fixture\n\n"
            "Priority: P2\n"
            "Agent: Developer / Tester / Reviewer / Fixer\n"
            "Status: IN_PROGRESS\n"
            "Dependencies: None\n\n"
            "Description:\nValidate cross-process Workflow CLI persistence.\n\n"
            "Acceptance Criteria:\n- [ ] Session is inspectable.\n"
        )
    store = tmp_path / "workflow-store"
    environment = os.environ | {"PYTHONPATH": str(source / "src")}
    created = subprocess.run(
        [
            sys.executable,
            "-m",
            "ai_os.cli",
            "workflow",
            "dry-run",
            "coding",
            "TASK-9999",
            "--objective",
            "validate architecture",
            "--root",
            str(repository),
            "--store",
            str(store),
            "--json",
        ],
        cwd=repository,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(created.stdout)
    assert payload["external_side_effects"] is False
    inspected_process = subprocess.run(
        [
            sys.executable,
            "-m",
            "ai_os.cli",
            "workflow",
            "session",
            payload["session_id"],
            "--store",
            str(store),
            "--json",
        ],
        cwd=repository,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    inspected = json.loads(inspected_process.stdout)
    assert inspected["workflow_status"] == "CREATED"


def test_workflow_pack_dry_run_across_processes(tmp_path: Path) -> None:
    source = Path(__file__).parent.parent
    store = tmp_path / "workflow-pack-store"
    environment = os.environ | {"PYTHONPATH": str(source / "src")}
    created = subprocess.run(
        [
            sys.executable,
            "-m",
            "ai_os.cli",
            "workflow",
            "dry-run",
            "investment",
            "TASK-0016",
            "--version",
            "1.0.0",
            "--objective",
            "dry-run governed investment research",
            "--root",
            str(source),
            "--store",
            str(store),
            "--json",
        ],
        cwd=source,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(created.stdout)
    assert payload["workflow"] == "investment@1.0.0"
    assert payload["external_side_effects"] is False


def test_workflow_unknown_name_fails_closed(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["workflow", "describe", "unknown", "--json"]) == 2
    assert "unknown Workflow" in json.loads(capsys.readouterr().out)["error"]
