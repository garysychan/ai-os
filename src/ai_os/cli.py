"""Command-line interface for the executable AI OS."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ai_os import __version__
from ai_os.governance import (
    ConsistencyReport,
    ControlPlane,
    ControlPlaneError,
    load_control_plane,
    run_consistency_checks,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aios",
        description="Governed AI OS runtime and Control Plane tools.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    commands = parser.add_subparsers(dest="command", required=True)

    bootstrap = commands.add_parser(
        "bootstrap",
        help="Load and validate the six Control Plane documents.",
    )
    _add_common_options(bootstrap)

    control_plane = commands.add_parser(
        "control-plane",
        help="Run Control Plane operations.",
    )
    control_commands = control_plane.add_subparsers(
        dest="control_command",
        required=True,
    )
    check = control_commands.add_parser(
        "check",
        help="Run the Control Plane consistency check.",
    )
    _add_common_options(check)

    return parser


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root containing the six Control Plane files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )


def _summary(
    control_plane: ControlPlane,
    report: ConsistencyReport,
) -> dict[str, Any]:
    status = report.status
    return {
        "operation": "CONTROL PLANE CONSISTENCY CHECK",
        "runtime_version": __version__,
        "root": str(control_plane.root),
        "status": status,
        "files": {
            "loaded": len(control_plane.documents),
            "required": 6,
            "names": list(control_plane.documents),
        },
        "agents": sorted(control_plane.agents),
        "rules": len(control_plane.rules),
        "workflow": {
            "stages": list(control_plane.workflow.stages),
            "states": sorted(control_plane.workflow.states),
            "transitions": [
                {"from": source, "to": target}
                for source, target in control_plane.workflow.transitions
            ],
        },
        "tasks": sorted(control_plane.tasks),
        "authority_domains": sorted(control_plane.authority_map),
        "warnings": [
            item.message
            for item in report.findings
            if item.severity.name == "WARNING"
        ],
        "consistency": report.to_dict(),
    }


def _print_human_report(
    control_plane: ControlPlane,
    report: ConsistencyReport,
    *,
    operation: str,
) -> None:
    status = report.status
    print(operation)
    print()
    print(f"Runtime Version: {__version__}")
    print(f"Root: {control_plane.root}")
    print(f"Files: {len(control_plane.documents)}/6")
    print(f"Agents: {len(control_plane.agents)}")
    print(f"Rules: {len(control_plane.rules)}")
    print(f"Workflow Stages: {len(control_plane.workflow.stages)}")
    print(f"Workflow States: {len(control_plane.workflow.states)}")
    print(f"Tasks: {len(control_plane.tasks)}")
    print(f"Authority Domains: {len(control_plane.authority_map)}")
    print(f"Status: {status}")

    if report.findings:
        print()
        print("Findings:")
        for finding in report.findings:
            subject = f" [{finding.subject}]" if finding.subject else ""
            print(
                f"- {finding.check_id} {finding.severity.name}"
                f" {finding.document}{subject}: {finding.message}"
            )
            if finding.evidence:
                print(f"  Evidence: {finding.evidence}")
            if finding.remediation:
                print(f"  Remediation: {finding.remediation}")


def _failure_payload(root: Path, error: ControlPlaneError) -> dict[str, str]:
    return {
        "operation": "CONTROL PLANE CONSISTENCY CHECK",
        "root": str(root.expanduser().resolve()),
        "status": "FAIL",
        "error_type": type(error).__name__,
        "error": str(error),
    }


def _run_load(
    root: Path,
    *,
    as_json: bool,
    operation: str,
) -> int:
    try:
        control_plane = load_control_plane(root)
    except ControlPlaneError as error:
        if as_json:
            print(
                json.dumps(
                    _failure_payload(root, error),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            print(operation)
            print()
            print(f"Root: {root.expanduser().resolve()}")
            print("Status: FAIL")
            print(f"Error: {error}")
        return 2

    report = run_consistency_checks(control_plane)

    if as_json:
        payload = _summary(control_plane, report)
        payload["operation"] = operation
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        _print_human_report(
            control_plane,
            report,
            operation=operation,
        )

    # WARNING is non-blocking; semantic FAIL blocks execution.
    return 2 if report.status == "FAIL" else 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the AI OS CLI and return a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "bootstrap":
        return _run_load(
            args.root,
            as_json=args.json,
            operation="AI OS CONTROL PLANE BOOTSTRAP",
        )

    if (
        args.command == "control-plane"
        and args.control_command == "check"
    ):
        return _run_load(
            args.root,
            as_json=args.json,
            operation="CONTROL PLANE CONSISTENCY CHECK",
        )

    parser.error("Unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
