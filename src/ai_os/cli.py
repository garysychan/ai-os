"""Command-line interface for the executable AI OS."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ai_os import __version__
from ai_os.agents import AgentRegistry, AgentRole, canonical_agents
from ai_os.governance import (
    ConsistencyReport,
    ControlPlane,
    ControlPlaneError,
    MissingControlPlaneFileError,
    TaskDefinition,
    load_control_plane,
    parse_tasks,
    run_consistency_checks,
)
from ai_os.tasks import (
    AcceptanceCriterion,
    Priority,
    Task,
    TaskError,
    TaskStatus,
    validate_task,
)
from ai_os.workflow import ALLOWED_TRANSITIONS


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

    task = commands.add_parser(
        "task",
        help="Validate tasks and inspect the executable state policy.",
    )
    task_commands = task.add_subparsers(
        dest="task_command",
        required=True,
    )
    task_validate = task_commands.add_parser(
        "validate",
        help="Parse and validate a TASKS.md file against the runtime schema.",
    )
    task_validate.add_argument(
        "path",
        type=Path,
        help="Path to the Markdown task registry.",
    )
    task_validate.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )
    task_transitions = task_commands.add_parser(
        "transitions",
        help="List every allowed task-state transition.",
    )
    task_transitions.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )

    agent = commands.add_parser(
        "agent",
        help="Inspect the executable Agent Runtime.",
    )
    agent_commands = agent.add_subparsers(
        dest="agent_command",
        required=True,
    )
    agent_list = agent_commands.add_parser(
        "list",
        help="List canonical executable Agents.",
    )
    agent_list.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )
    agent_describe = agent_commands.add_parser(
        "describe",
        help="Describe one canonical Agent role.",
    )
    agent_describe.add_argument("role", help="Canonical Agent role name.")
    agent_describe.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )

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


def _failure_payload(root: Path, error: ControlPlaneError) -> dict[str, Any]:
    check_id = (
        "CP-C01"
        if isinstance(error, MissingControlPlaneFileError)
        else "CP-C02"
    )
    finding = {
        "check_id": check_id,
        "severity": "FAIL",
        "document": "CONTROL_PLANE",
        "subject": None,
        "message": str(error),
        "evidence": type(error).__name__,
        "remediation": "Correct the input documents and rerun bootstrap",
    }
    return {
        "operation": "CONTROL PLANE CONSISTENCY CHECK",
        "root": str(root.expanduser().resolve()),
        "status": "FAIL",
        "error_type": type(error).__name__,
        "error": str(error),
        "consistency": {
            "status": "FAIL",
            "checks": [f"CP-C{number:02d}" for number in range(1, 11)],
            "findings": [finding],
        },
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



def _runtime_task(definition: TaskDefinition) -> Task:
    """Convert a parsed Markdown task to the canonical runtime schema."""
    status = TaskStatus(definition.status) if definition.status else TaskStatus.TODO
    criteria = tuple(
        AcceptanceCriterion(
            description=item,
            completed=status is TaskStatus.DONE,
        )
        for item in definition.acceptance_criteria
    )
    evidence = (
        ("TASKS.md records completed acceptance criteria",)
        if status is TaskStatus.DONE
        else ()
    )
    return Task(
        task_id=definition.task_id,
        title=definition.title,
        priority=Priority(definition.priority or "P2"),
        status=status,
        agents=definition.agents,
        dependencies=definition.dependencies,
        acceptance_criteria=criteria,
        completion_evidence=evidence,
    )


def _run_task_validate(path: Path, *, as_json: bool) -> int:
    resolved = path.expanduser().resolve()
    try:
        markdown = resolved.read_text(encoding="utf-8")
        definitions = parse_tasks(markdown)
        tasks = tuple(
            validate_task(_runtime_task(definition))
            for definition in definitions.values()
        )
    except (OSError, UnicodeError, ValueError, ControlPlaneError, TaskError) as error:
        payload = {
            "operation": "TASK SCHEMA VALIDATION",
            "path": str(resolved),
            "status": "FAIL",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        if as_json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print("TASK SCHEMA VALIDATION")
            print()
            print(f"Path: {resolved}")
            print("Status: FAIL")
            print(f"Error: {error}")
        return 2

    payload = {
        "operation": "TASK SCHEMA VALIDATION",
        "path": str(resolved),
        "status": "PASS",
        "tasks": [
            {
                "task_id": task.task_id,
                "status": task.status.value,
                "priority": task.priority.value,
                "agents": list(task.agents),
                "dependencies": list(task.dependencies),
                "acceptance_criteria": len(task.acceptance_criteria),
            }
            for task in tasks
        ],
    }
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("TASK SCHEMA VALIDATION")
        print()
        print(f"Path: {resolved}")
        print(f"Tasks: {len(tasks)}")
        print("Status: PASS")
    return 0


def _run_task_transitions(*, as_json: bool) -> int:
    transitions = sorted(
        (
            {"from": source.value, "to": target.value}
            for source, target in ALLOWED_TRANSITIONS
        ),
        key=lambda item: (item["from"], item["to"]),
    )
    if as_json:
        print(
            json.dumps(
                {
                    "operation": "TASK STATE TRANSITIONS",
                    "status": "PASS",
                    "transitions": transitions,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print("TASK STATE TRANSITIONS")
        print()
        for transition in transitions:
            print(f"{transition['from']} -> {transition['to']}")
        print()
        print(f"Transitions: {len(transitions)}")
        print("Status: PASS")
    return 0

def _agent_payload(role: AgentRole) -> dict[str, Any]:
    registry = AgentRegistry(canonical_agents())
    descriptor = registry.get(role).descriptor
    return {
        "role": descriptor.role.value,
        "capabilities": sorted(item.value for item in descriptor.capabilities),
        "permissions": sorted(item.value for item in descriptor.permissions),
        "description": descriptor.description,
    }


def _run_agent_list(*, as_json: bool) -> int:
    payload = [_agent_payload(role) for role in AgentRole]
    payload.sort(key=lambda item: item["role"])
    if as_json:
        print(json.dumps(
            {"operation": "AGENT LIST", "status": "PASS", "agents": payload},
            indent=2,
            ensure_ascii=False,
        ))
    else:
        print("AGENT LIST")
        print()
        for item in payload:
            capabilities = ", ".join(item["capabilities"])
            print(f"{item['role']}: {capabilities}")
        print()
        print(f"Agents: {len(payload)}")
        print("Status: PASS")
    return 0


def _run_agent_describe(role_name: str, *, as_json: bool) -> int:
    try:
        role = next(
            item for item in AgentRole
            if item.value.casefold() == role_name.strip().casefold()
        )
    except StopIteration:
        choices = ", ".join(item.value for item in AgentRole)
        if as_json:
            print(json.dumps({
                "operation": "AGENT DESCRIBE",
                "status": "FAIL",
                "error": f"Unknown Agent role: {role_name}",
                "allowed_roles": [item.value for item in AgentRole],
            }, indent=2, ensure_ascii=False))
        else:
            print("AGENT DESCRIBE")
            print()
            print("Status: FAIL")
            print(f"Error: Unknown Agent role: {role_name}")
            print(f"Allowed: {choices}")
        return 2

    payload = _agent_payload(role)
    if as_json:
        print(json.dumps(
            {"operation": "AGENT DESCRIBE", "status": "PASS", **payload},
            indent=2,
            ensure_ascii=False,
        ))
    else:
        print("AGENT DESCRIBE")
        print()
        print(f"Role: {payload['role']}")
        print(f"Description: {payload['description']}")
        print("Capabilities: " + ", ".join(payload["capabilities"]))
        print("Permissions: " + ", ".join(payload["permissions"]))
        print("Status: PASS")
    return 0


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

    if args.command == "task" and args.task_command == "validate":
        return _run_task_validate(args.path, as_json=args.json)

    if args.command == "task" and args.task_command == "transitions":
        return _run_task_transitions(as_json=args.json)

    if args.command == "agent" and args.agent_command == "list":
        return _run_agent_list(as_json=args.json)

    if args.command == "agent" and args.agent_command == "describe":
        return _run_agent_describe(args.role, as_json=args.json)

    parser.error("Unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
