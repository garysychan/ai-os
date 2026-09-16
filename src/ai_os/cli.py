"""Command-line interface for the executable AI OS."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_os import __version__
from ai_os.agents import (
    AgentRegistry,
    AgentRole,
    AgentRouter,
    AgentRuntime,
    Capability,
    Permission,
    canonical_agents,
)
from ai_os.controller import (
    ControllerEngine,
    ControllerError,
    ControllerValidationError,
    InMemorySessionStore,
)
from ai_os.execution import (
    AdapterRegistry,
    ExecutionContext,
    ExecutionEngine,
    ExecutionEngineError,
    ExecutionPlan,
    ExecutionStep,
    ExecutionValidationError,
    InMemoryExecutionStore,
    NoOpAdapter,
)
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

_SESSION_STORE = InMemorySessionStore()
_EXECUTION_STORE = InMemoryExecutionStore()


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

    run = commands.add_parser("run", help="Create a governed Controller session.")
    run.add_argument("task_id", help="Task identifier from TASKS.md.")
    run.add_argument("--objective", required=True, help="Explicit execution objective.")
    run.add_argument("--root", type=Path, default=Path.cwd())
    run.add_argument(
        "--dry-run",
        action="store_true",
        required=True,
        help="Validate and create a side-effect-free in-memory session.",
    )
    run.add_argument("--json", action="store_true")

    session = commands.add_parser("session", help="Inspect process-local sessions.")
    session_commands = session.add_subparsers(dest="session_command", required=True)
    for command in ("show", "trace"):
        inspect = session_commands.add_parser(command)
        inspect.add_argument("session_id")
        inspect.add_argument("--json", action="store_true")

    execute = commands.add_parser("execute", help="Execute an approved plan through safe adapters.")
    execute.add_argument("task_id")
    execute.add_argument("--plan", type=Path, required=True)
    execute.add_argument("--root", type=Path, default=Path.cwd())
    execute.add_argument("--dry-run", action="store_true", required=True)
    execute.add_argument("--json", action="store_true")

    execution = commands.add_parser("execution", help="Validate and inspect execution sessions.")
    execution_commands = execution.add_subparsers(dest="execution_command", required=True)
    execution_validate = execution_commands.add_parser("validate")
    execution_validate.add_argument("plan", type=Path)
    execution_validate.add_argument("--root", type=Path, default=Path.cwd())
    execution_validate.add_argument("--json", action="store_true")
    execution_adapters = execution_commands.add_parser("adapters")
    execution_adapters.add_argument("--json", action="store_true")
    for command in ("show", "trace"):
        inspect = execution_commands.add_parser(command)
        inspect.add_argument("execution_id")
        inspect.add_argument("--json", action="store_true")

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
        "warnings": [item.message for item in report.findings if item.severity.name == "WARNING"],
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
    check_id = "CP-C01" if isinstance(error, MissingControlPlaneFileError) else "CP-C02"
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
        ("TASKS.md records completed acceptance criteria",) if status is TaskStatus.DONE else ()
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
            validate_task(_runtime_task(definition)) for definition in definitions.values()
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
        ({"from": source.value, "to": target.value} for source, target in ALLOWED_TRANSITIONS),
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
        print(
            json.dumps(
                {"operation": "AGENT LIST", "status": "PASS", "agents": payload},
                indent=2,
                ensure_ascii=False,
            )
        )
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


def _session_payload(session_id: str, *, trace_only: bool = False) -> dict[str, Any]:
    session = _SESSION_STORE.get(session_id)
    events = [
        {
            "sequence": event.sequence,
            "type": event.event_type.value,
            "stage": event.stage.value,
            "actor": event.actor.value,
            "timestamp": event.timestamp.isoformat(),
            "reason": event.reason,
            "evidence": list(event.evidence),
        }
        for event in session.events
    ]
    if trace_only:
        return {"session_id": session.session_id, "events": events}
    return {
        "session_id": session.session_id,
        "task_id": session.task_id,
        "objective": session.objective,
        "stage": session.stage.value,
        "task_status": session.task_status.value,
        "outcome": session.outcome.value if session.outcome else None,
        "fix_attempts": session.fix_attempts,
        "max_fix_attempts": session.max_fix_attempts,
        "events": events,
    }


def _run_controller_dry_run(
    task_id: str,
    objective: str,
    root: Path,
    *,
    as_json: bool,
) -> int:
    try:
        control_plane = load_control_plane(root)
        definitions = control_plane.tasks
        definition = definitions[task_id]
        task = _runtime_task(definition)
        dependency_states = {
            dependency: TaskStatus(definitions[dependency].status or "TODO")
            for dependency in task.dependencies
        }
        registry = AgentRegistry(canonical_agents())
        engine = ControllerEngine(AgentRuntime(AgentRouter(registry)))
        session = engine.start(
            task,
            objective,
            dependency_states=dependency_states,
            started_at=datetime.now(UTC),
            approval_evidence=("dry-run: no external side effects authorized",),
        )
        _SESSION_STORE.save(session)
    except (KeyError, ValueError, ControlPlaneError, ControllerError) as error:
        payload = {"operation": "CONTROLLER DRY RUN", "status": "FAIL", "error": str(error)}
        print(
            json.dumps(payload, indent=2)
            if as_json
            else f"CONTROLLER DRY RUN\nStatus: FAIL\nError: {error}"
        )
        return 2
    payload = {
        "operation": "CONTROLLER DRY RUN",
        "status": "PASS",
        **_session_payload(session.session_id),
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print("CONTROLLER DRY RUN")
        print(f"Session: {session.session_id}")
        print(f"Task: {session.task_id}")
        print("Side Effects: NONE")
        print("Status: PASS")
    return 0


def _run_session_inspect(session_id: str, *, trace_only: bool, as_json: bool) -> int:
    try:
        payload = _session_payload(session_id, trace_only=trace_only)
    except ControllerValidationError as error:
        payload = {"status": "FAIL", "error": str(error)}
        print(json.dumps(payload, indent=2) if as_json else f"Status: FAIL\nError: {error}")
        return 2
    if as_json:
        print(json.dumps({"status": "PASS", **payload}, indent=2))
    else:
        print("SESSION TRACE" if trace_only else "SESSION SHOW")
        print(f"Session: {session_id}")
        print(f"Events: {len(payload['events'])}")
        print("Status: PASS")
    return 0


def _load_execution_plan(path: Path) -> ExecutionPlan:
    raw = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("steps"), list):
        raise ExecutionValidationError("plan JSON must be an object with a steps array")
    steps = []
    for item in raw["steps"]:
        if not isinstance(item, dict):
            raise ExecutionValidationError("each execution step must be an object")
        inputs = item.get("inputs", {})
        if not isinstance(inputs, dict):
            raise ExecutionValidationError("step inputs must be an object")
        idempotent = item.get("idempotent", False)
        retries = item.get("max_retries", 0)
        if not isinstance(idempotent, bool):
            raise ExecutionValidationError("step idempotent must be a boolean")
        if isinstance(retries, bool) or not isinstance(retries, int):
            raise ExecutionValidationError("step max_retries must be an integer")
        steps.append(
            ExecutionStep(
                step_id=str(item.get("step_id", "")),
                adapter=str(item.get("adapter", "")),
                operation=str(item.get("operation", "")),
                agent_role=AgentRole(str(item.get("agent_role", ""))),
                capability=Capability(str(item.get("capability", ""))),
                required_permission=Permission(str(item.get("required_permission", ""))),
                inputs=tuple(sorted((str(key), str(value)) for key, value in inputs.items())),
                idempotent=idempotent,
                max_retries=retries,
            )
        )
    max_steps = raw.get("max_steps", len(steps))
    if isinstance(max_steps, bool) or not isinstance(max_steps, int):
        raise ExecutionValidationError("plan max_steps must be an integer")
    return ExecutionPlan(
        plan_id=str(raw.get("plan_id", "")),
        task_id=str(raw.get("task_id", "")),
        steps=tuple(steps),
        max_steps=max_steps,
    )


def _safe_execution_registry(plan: ExecutionPlan) -> AdapterRegistry:
    operations: dict[str, set[str]] = {}
    for step in plan.steps:
        operations.setdefault(step.adapter, set()).add(step.operation)
    return AdapterRegistry(
        NoOpAdapter(name, frozenset(items)) for name, items in sorted(operations.items())
    )


def _execution_session_payload(execution_id: str, *, trace_only: bool = False) -> dict[str, Any]:
    session = _EXECUTION_STORE.get(execution_id)
    events = [
        {
            "sequence": event.sequence,
            "type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "reason": event.reason,
            "step_id": event.step_id,
            "attempt": event.attempt,
            "evidence": list(event.evidence),
        }
        for event in session.events
    ]
    if trace_only:
        return {"execution_id": execution_id, "events": events}
    return {
        "execution_id": execution_id,
        "plan_id": session.plan_id,
        "task_id": session.task_id,
        "controller_session_id": session.controller_session_id,
        "outcome": session.outcome.value if session.outcome else None,
        "results": len(session.results),
        "events": events,
    }


def _execution_inputs(root: Path, plan: ExecutionPlan) -> tuple[Task, dict[str, TaskStatus]]:
    control_plane = load_control_plane(root)
    definition = control_plane.tasks[plan.task_id]
    task = _runtime_task(definition)
    dependencies = {
        item: TaskStatus(control_plane.tasks[item].status or "TODO") for item in task.dependencies
    }
    return task, dependencies


def _run_execution_dry_run(
    task_id: str,
    plan_path: Path,
    root: Path,
    *,
    as_json: bool,
) -> int:
    try:
        plan = _load_execution_plan(plan_path)
        if plan.task_id != task_id:
            raise ExecutionValidationError("CLI task ID does not match plan task_id")
        task, dependencies = _execution_inputs(root, plan)
        session, result = ExecutionEngine(_safe_execution_registry(plan)).run(
            task,
            plan,
            ExecutionContext(
                controller_session_id="cli-dry-run",
                objective="validate and dry-run approved execution plan",
                approval_evidence=("dry-run: no external side effects authorized",),
            ),
            dependency_states=dependencies,
        )
        _EXECUTION_STORE.save(session)
        payload = {
            "operation": "EXECUTION DRY RUN",
            "status": "PASS",
            "side_effects": "NONE",
            **_execution_session_payload(session.execution_id),
            "result": result.outcome.value,
        }
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        ValueError,
        ControlPlaneError,
        ExecutionEngineError,
    ) as error:
        payload = {"operation": "EXECUTION DRY RUN", "status": "FAIL", "error": str(error)}
        print(
            json.dumps(payload, indent=2)
            if as_json
            else f"EXECUTION DRY RUN\nStatus: FAIL\nError: {error}"
        )
        return 2
    print(
        json.dumps(payload, indent=2)
        if as_json
        else (
            "EXECUTION DRY RUN\n"
            f"Execution: {session.execution_id}\n"
            "Side Effects: NONE\nStatus: PASS"
        )
    )
    return 0


def _run_execution_validate(plan_path: Path, root: Path, *, as_json: bool) -> int:
    try:
        plan = _load_execution_plan(plan_path)
        task, dependencies = _execution_inputs(root, plan)
        now = datetime.now(UTC)
        context = ExecutionContext("cli-validation", "validate execution plan")
        engine = ExecutionEngine(_safe_execution_registry(plan))
        engine.policy.validate_start(task, plan, context, dependencies, now)
        for step in plan.steps:
            engine.policy.validate_adapter(engine.registry.resolve(step.adapter, step.operation))
        payload = {
            "operation": "EXECUTION PLAN VALIDATION",
            "status": "PASS",
            "plan_id": plan.plan_id,
            "steps": len(plan.steps),
        }
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        ValueError,
        ControlPlaneError,
        ExecutionEngineError,
    ) as error:
        payload = {"operation": "EXECUTION PLAN VALIDATION", "status": "FAIL", "error": str(error)}
        print(
            json.dumps(payload, indent=2)
            if as_json
            else f"EXECUTION PLAN VALIDATION\nStatus: FAIL\nError: {error}"
        )
        return 2
    print(
        json.dumps(payload, indent=2)
        if as_json
        else (
            "EXECUTION PLAN VALIDATION\n"
            f"Plan: {plan.plan_id}\nSteps: {len(plan.steps)}\nStatus: PASS"
        )
    )
    return 0


def _run_execution_inspect(execution_id: str, *, trace_only: bool, as_json: bool) -> int:
    try:
        payload = _execution_session_payload(execution_id, trace_only=trace_only)
    except ExecutionValidationError as error:
        payload = {"status": "FAIL", "error": str(error)}
        print(json.dumps(payload, indent=2) if as_json else f"Status: FAIL\nError: {error}")
        return 2
    print(
        json.dumps({"status": "PASS", **payload}, indent=2)
        if as_json
        else (
            f"EXECUTION {'TRACE' if trace_only else 'SHOW'}\n"
            f"Execution: {execution_id}\n"
            f"Events: {len(payload['events'])}\nStatus: PASS"
        )
    )
    return 0


def _run_agent_describe(role_name: str, *, as_json: bool) -> int:
    try:
        role = next(
            item for item in AgentRole if item.value.casefold() == role_name.strip().casefold()
        )
    except StopIteration:
        choices = ", ".join(item.value for item in AgentRole)
        if as_json:
            print(
                json.dumps(
                    {
                        "operation": "AGENT DESCRIBE",
                        "status": "FAIL",
                        "error": f"Unknown Agent role: {role_name}",
                        "allowed_roles": [item.value for item in AgentRole],
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            print("AGENT DESCRIBE")
            print()
            print("Status: FAIL")
            print(f"Error: Unknown Agent role: {role_name}")
            print(f"Allowed: {choices}")
        return 2

    payload = _agent_payload(role)
    if as_json:
        print(
            json.dumps(
                {"operation": "AGENT DESCRIBE", "status": "PASS", **payload},
                indent=2,
                ensure_ascii=False,
            )
        )
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

    if args.command == "control-plane" and args.control_command == "check":
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

    if args.command == "run":
        return _run_controller_dry_run(
            args.task_id,
            args.objective,
            args.root,
            as_json=args.json,
        )

    if args.command == "session":
        return _run_session_inspect(
            args.session_id,
            trace_only=args.session_command == "trace",
            as_json=args.json,
        )

    if args.command == "execute":
        return _run_execution_dry_run(
            args.task_id,
            args.plan,
            args.root,
            as_json=args.json,
        )

    if args.command == "execution" and args.execution_command == "validate":
        return _run_execution_validate(args.plan, args.root, as_json=args.json)

    if args.command == "execution" and args.execution_command == "adapters":
        payload = {
            "operation": "EXECUTION ADAPTERS",
            "status": "PASS",
            "adapters": ["noop"],
            "external_side_effects": False,
        }
        print(
            json.dumps(payload, indent=2)
            if args.json
            else "EXECUTION ADAPTERS\nnoop: side-effect-free\nStatus: PASS"
        )
        return 0

    if args.command == "execution":
        return _run_execution_inspect(
            args.execution_id,
            trace_only=args.execution_command == "trace",
            as_json=args.json,
        )

    parser.error("Unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
