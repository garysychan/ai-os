from __future__ import annotations

import json
from pathlib import Path

from ai_os.cli import main


def active_task_root(tmp_path: Path) -> str:
    root = tmp_path / "control-plane"
    root.mkdir()
    (root / "TASKS.md").write_text(
        """## TASK-0019 — Scheduler CLI fixture

Priority: P1
Agent: Controller / Tester
Status: REVIEW
Dependencies: None

Acceptance Criteria:
- [x] Fixture is dispatchable.
""",
        encoding="utf-8",
    )
    return str(root)


def create_args(database: str, root: str) -> list[str]:
    return [
        "scheduler",
        "create",
        "job-cli-1",
        "TASK-0019",
        "coding",
        "--run-at",
        "2099-01-01T00:00:00+00:00",
        "--database",
        database,
        "--root",
        root,
        "--actor-role",
        "Controller",
        "--json",
    ]


def test_scheduler_cli_create_list_show_and_cancel(tmp_path, capsys) -> None:
    database = str(tmp_path / "runtime.db")
    root = active_task_root(tmp_path)
    assert main(create_args(database, root)) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["job"]["state"] == "SCHEDULED"

    assert (
        main(
            [
                "scheduler",
                "list",
                "--database",
                database,
                "--root",
                root,
                "--actor-role",
                "Reviewer",
                "--json",
            ]
        )
        == 0
    )
    listed = json.loads(capsys.readouterr().out)
    assert [item["job_id"] for item in listed["jobs"]] == ["job-cli-1"]

    assert (
        main(
            [
                "scheduler",
                "cancel",
                "job-cli-1",
                "--database",
                database,
                "--root",
                root,
                "--actor-role",
                "Controller",
                "--json",
            ]
        )
        == 0
    )
    cancelled = json.loads(capsys.readouterr().out)
    assert cancelled["job"]["state"] == "CANCELLED"


def test_scheduler_cli_rejects_unauthorized_create(tmp_path, capsys) -> None:
    args = create_args(str(tmp_path / "runtime.db"), active_task_root(tmp_path))
    args[args.index("Controller")] = "Reviewer"

    assert main(args) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["error_type"] == "SchedulerAuthorizationError"


def test_scheduler_claim_dry_run_does_not_mutate(tmp_path, capsys) -> None:
    database = str(tmp_path / "runtime.db")
    root = active_task_root(tmp_path)
    assert main(create_args(database, root)) == 0
    capsys.readouterr()

    assert (
        main(
            [
                "scheduler",
                "claim",
                "--worker-id",
                "worker-cli",
                "--dry-run",
                "--database",
                database,
                "--root",
                root,
                "--actor-role",
                "Controller",
                "--json",
            ]
        )
        == 0
    )
    preview = json.loads(capsys.readouterr().out)
    assert preview["would_claim"] is None

    assert (
        main(
            [
                "scheduler",
                "show",
                "job-cli-1",
                "--database",
                database,
                "--root",
                root,
                "--actor-role",
                "Reviewer",
                "--json",
            ]
        )
        == 0
    )
    shown = json.loads(capsys.readouterr().out)
    assert shown["job"]["state"] == "SCHEDULED"
