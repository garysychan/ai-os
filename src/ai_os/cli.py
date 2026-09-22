"""Command-line interface for the executable AI OS."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ai_os import __version__
from ai_os.adapters import (
    AdapterError,
    AdapterInvocation,
    AdapterService,
    ReadOnlyFileAdapter,
)
from ai_os.adapters import (
    AdapterRegistry as CoreAdapterRegistry,
)
from ai_os.agents import (
    AgentRegistry,
    AgentRole,
    AgentRouter,
    AgentRuntime,
    Capability,
    Permission,
    PermissionPolicy,
    canonical_agents,
)
from ai_os.config import (
    PROFILE_DEFAULTS,
    ConfigurationError,
    EnvironmentProfile,
    load_config_file,
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
from ai_os.monitoring import MonitoringError, MonitoringQueryContext, MonitoringService
from ai_os.observability import (
    AuditQueryContext,
    ObservabilityError,
    RuntimeEvent,
    RuntimeEventFilter,
    RuntimeEventSource,
    RuntimeEventType,
    authorize_query,
)
from ai_os.persistence import (
    PersistenceError,
    PersistenceNotFoundError,
    SQLiteRuntimeStore,
    StoreConfig,
)
from ai_os.scheduler import (
    JobSpec,
    ScheduleKind,
    SchedulerContext,
    SchedulerError,
    SchedulerService,
    SQLiteSchedulerStore,
)

from ai_os.secrets import (
    EnvironmentSecretProvider,
    SecretAccessContext,
    SecretError,
    SecretReference,
    SecretService,
)

from ai_os.tasks import (
    AcceptanceCriterion,
    Priority,
    Task,
    TaskError,
    TaskStatus,
    validate_task,
)
from ai_os.tools import ToolError, ToolRegistry, core_tools
from ai_os.workflow import ALLOWED_TRANSITIONS
from ai_os.workflows import (
    JsonWorkflowStore,
    WorkflowEngine,
    WorkflowError,
    WorkflowRegistry,
    WorkflowStage,
    core_workflows,
    validate_definition,
)
from ai_os.workflows import (
    WorkflowDefinition as RuntimeWorkflowDefinition,
)

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

    adapter = commands.add_parser("adapter", help="Inspect and dry-run governed Adapters.")
    adapter_commands = adapter.add_subparsers(dest="adapter_command", required=True)
    adapter_list = adapter_commands.add_parser("list")
    adapter_list.add_argument("--root", type=Path, default=Path.cwd())
    adapter_list.add_argument("--json", action="store_true")
    adapter_describe = adapter_commands.add_parser("describe")
    adapter_describe.add_argument("name")
    adapter_describe.add_argument("--version", default="1")
    adapter_describe.add_argument("--root", type=Path, default=Path.cwd())
    adapter_describe.add_argument("--json", action="store_true")
    adapter_validate = adapter_commands.add_parser("validate")
    adapter_validate.add_argument("name")
    adapter_validate.add_argument("--version", default="1")
    adapter_validate.add_argument("--root", type=Path, default=Path.cwd())
    adapter_validate.add_argument("--json", action="store_true")
    adapter_dry_run = adapter_commands.add_parser("dry-run")
    adapter_dry_run.add_argument("name")
    adapter_dry_run.add_argument("--version", default="1")
    adapter_dry_run.add_argument("--root", type=Path, required=True)
    adapter_dry_run.add_argument("--path", type=Path, required=True)
    adapter_dry_run.add_argument("--task-id", default="TASK-0012")
    adapter_dry_run.add_argument("--json", action="store_true")

    tool = commands.add_parser("tool", help="Inspect the governed Tool Registry.")
    tool_commands = tool.add_subparsers(dest="tool_command", required=True)
    tool_list = tool_commands.add_parser("list")
    tool_list.add_argument("--root", type=Path, default=Path.cwd())
    tool_list.add_argument("--json", action="store_true")
    tool_describe = tool_commands.add_parser("describe")
    tool_describe.add_argument("name")
    tool_describe.add_argument("--version", default="1")
    tool_describe.add_argument("--root", type=Path, default=Path.cwd())
    tool_describe.add_argument("--json", action="store_true")
    tool_validate = tool_commands.add_parser("validate")
    tool_validate.add_argument("name")
    tool_validate.add_argument("--version", default="1")
    tool_validate.add_argument("--root", type=Path, default=Path.cwd())
    tool_validate.add_argument("--json", action="store_true")

    workflow = commands.add_parser("workflow", help="Inspect governed Workflows.")
    workflow_commands = workflow.add_subparsers(dest="workflow_command", required=True)
    workflow_list = workflow_commands.add_parser("list")
    workflow_list.add_argument("--json", action="store_true")
    workflow_describe = workflow_commands.add_parser("describe")
    workflow_describe.add_argument("name")
    workflow_describe.add_argument("--version", default="1")
    workflow_describe.add_argument("--json", action="store_true")
    workflow_validate = workflow_commands.add_parser("validate")
    workflow_validate.add_argument("definition", type=Path)
    workflow_validate.add_argument("--json", action="store_true")
    workflow_dry_run = workflow_commands.add_parser("dry-run")
    workflow_dry_run.add_argument("name")
    workflow_dry_run.add_argument("task_id")
    workflow_dry_run.add_argument("--version", default="1")
    workflow_dry_run.add_argument("--objective", required=True)
    workflow_dry_run.add_argument("--root", type=Path, default=Path.cwd())
    workflow_dry_run.add_argument("--store", type=Path)
    workflow_dry_run.add_argument("--json", action="store_true")
    workflow_session = workflow_commands.add_parser("session")
    workflow_session.add_argument("session_id")
    workflow_session.add_argument("--store", type=Path, default=Path(".ai-os/workflows"))
    workflow_session.add_argument("--json", action="store_true")

    store = commands.add_parser("store", help="Manage an explicit SQLite runtime store.")
    store_commands = store.add_subparsers(dest="store_command", required=True)
    for command in ("init", "status", "migrate"):
        store_command = store_commands.add_parser(command)
        store_command.add_argument("--database", type=Path, required=True)
        store_command.add_argument("--json", action="store_true")
    store_session = store_commands.add_parser("session")
    store_session.add_argument("session_id")
    store_session.add_argument("--database", type=Path, required=True)
    store_session.add_argument("--json", action="store_true")
    store_execution = store_commands.add_parser("execution")
    store_execution.add_argument("execution_id")
    store_execution.add_argument("--database", type=Path, required=True)
    store_execution.add_argument("--json", action="store_true")
    store_audit = store_commands.add_parser("audit")
    store_audit.add_argument("--invocation-id")
    store_audit.add_argument("--limit", type=int, default=100)
    store_audit.add_argument("--database", type=Path, required=True)
    store_audit.add_argument("--json", action="store_true")

    audit = commands.add_parser("audit", help="Inspect canonical runtime audit evidence.")
    audit_commands = audit.add_subparsers(dest="audit_command", required=True)
    audit_list = audit_commands.add_parser("list")
    audit_list.add_argument("--database", type=Path, required=True)
    audit_list.add_argument("--task-id")
    audit_list.add_argument("--trace-id")
    audit_list.add_argument("--execution-id")
    audit_list.add_argument("--invocation-id")
    audit_list.add_argument("--event-type", choices=[item.value for item in RuntimeEventType])
    audit_list.add_argument("--source", choices=[item.value for item in RuntimeEventSource])
    audit_list.add_argument("--limit", type=int, default=100)
    audit_list.add_argument("--json", action="store_true")
    audit_list.add_argument(
        "--actor-role", required=True, choices=[role.value for role in AgentRole]
    )
    audit_show = audit_commands.add_parser("show")
    audit_show.add_argument("event_id")
    audit_show.add_argument("--database", type=Path, required=True)
    audit_show.add_argument("--json", action="store_true")
    audit_show.add_argument(
        "--actor-role", required=True, choices=[role.value for role in AgentRole]
    )

    trace = commands.add_parser("trace", help="Reconstruct a canonical runtime trace.")
    trace_commands = trace.add_subparsers(dest="trace_command", required=True)
    trace_show = trace_commands.add_parser("show")
    trace_show.add_argument("trace_id")
    trace_show.add_argument("--database", type=Path, required=True)
    trace_show.add_argument("--limit", type=int, default=100)
    trace_show.add_argument("--json", action="store_true")
    trace_show.add_argument(
        "--actor-role", required=True, choices=[role.value for role in AgentRole]
    )

    health = commands.add_parser("health", help="Inspect governed runtime health.")
    health.add_argument("--database", type=Path, required=True)
    health.add_argument("--actor-role", required=True, choices=[role.value for role in AgentRole])
    health.add_argument("--stale-seconds", type=int, default=900)
    health.add_argument("--json", action="store_true")

    metrics = commands.add_parser("metrics", help="Inspect bounded runtime metrics.")
    metrics.add_argument("--database", type=Path, required=True)
    metrics.add_argument("--actor-role", required=True, choices=[role.value for role in AgentRole])
    metrics.add_argument("--window-seconds", type=int, default=3600)
    metrics.add_argument("--json", action="store_true")


    config = commands.add_parser("config", help="Validate governed runtime configuration.")
    config_commands = config.add_subparsers(dest="config_command", required=True)
    config_profiles = config_commands.add_parser("profiles")
    config_profiles.add_argument("--json", action="store_true")
    for command in ("validate", "show", "resolve"):
        action = config_commands.add_parser(command)
        action.add_argument("configuration", type=Path)
        action.add_argument(
            "--profile",
            default=EnvironmentProfile.DEVELOPMENT.value,
            choices=[item.value for item in EnvironmentProfile],
        )
        if command in {"show", "resolve"}:
            action.add_argument(
                "--actor-role", required=True, choices=[role.value for role in AgentRole]
            )
        if command == "resolve":
            action.add_argument("--dry-run", action="store_true", required=True)
        action.add_argument("--json", action="store_true")

    secrets = commands.add_parser("secrets", help="Check an authorized secret reference.")
    secrets_commands = secrets.add_subparsers(dest="secrets_command", required=True)
    secrets_check = secrets_commands.add_parser("check")
    secrets_check.add_argument("reference")
    secrets_check.add_argument(
        "--actor-role", required=True, choices=[role.value for role in AgentRole]
    )
    secrets_check.add_argument("--json", action="store_true")


    scheduler = commands.add_parser("scheduler", help="Manage governed background jobs.")
    scheduler_commands = scheduler.add_subparsers(dest="scheduler_command", required=True)
    scheduler_create = scheduler_commands.add_parser("create")
    scheduler_create.add_argument("job_id")
    scheduler_create.add_argument("task_id")
    scheduler_create.add_argument("workflow")
    scheduler_create.add_argument("--version", default="1")
    scheduler_create.add_argument("--run-at", required=True)
    scheduler_create.add_argument("--interval-seconds", type=int)
    scheduler_create.add_argument("--max-attempts", type=int, default=1)
    scheduler_create.add_argument("--retry-backoff-seconds", type=int, default=30)
    scheduler_create.add_argument("--timeout-seconds", type=int, default=300)
    scheduler_create.add_argument("--max-elapsed-seconds", type=int, default=86_400)
    scheduler_create.add_argument("--jitter-seconds", type=int, default=0)
    scheduler_create.add_argument("--root", type=Path, default=Path.cwd())
    scheduler_create.add_argument("--database", type=Path, required=True)
    scheduler_create.add_argument(
        "--actor-role", required=True, choices=[role.value for role in AgentRole]
    )
    scheduler_create.add_argument("--json", action="store_true")
    for command in ("list", "show", "cancel", "claim"):
        action = scheduler_commands.add_parser(command)
        if command in {"show", "cancel"}:
            action.add_argument("job_id")
        if command == "claim":
            action.add_argument("--worker-id", required=True)
            action.add_argument("--lease-seconds", type=int, default=60)
            action.add_argument("--dry-run", action="store_true", required=True)
        action.add_argument("--root", type=Path, default=Path.cwd())
        action.add_argument("--database", type=Path, required=True)
        action.add_argument(
            "--actor-role", required=True, choices=[role.value for role in AgentRole]
        )
        action.add_argument("--limit", type=int, default=100)
        action.add_argument("--json", action="store_true")

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


def _core_adapter_registry(root: Path) -> CoreAdapterRegistry:
    resolved = root.expanduser().resolve(strict=True)
    return CoreAdapterRegistry((ReadOnlyFileAdapter((resolved,)),))


def _core_tool_registry(root: Path) -> ToolRegistry:
    return ToolRegistry(_core_adapter_registry(root), core_tools())


def _tool_metadata_payload(metadata: Any) -> dict[str, Any]:
    return {
        "name": metadata.name,
        "version": metadata.version,
        "description": metadata.description,
        "operations": [
            {
                "name": item.name,
                "capability": item.capability.value,
                "required_permission": item.required_permission.value,
                "risk": item.risk.value,
                "side_effect": item.side_effect.value,
                "idempotent": item.idempotent,
                "approval_required": item.approval_required,
                "adapter": f"{item.adapter}@{item.adapter_version}",
                "adapter_operation": item.adapter_operation,
            }
            for item in metadata.operations
        ],
    }


def _run_tool_inspect(
    command: str,
    root: Path,
    *,
    name: str | None = None,
    version: str = "1",
    as_json: bool,
) -> int:
    try:
        registry = _core_tool_registry(root)
        if command == "list":
            tools = [_tool_metadata_payload(item) for item in registry.list_metadata()]
        else:
            tools = [_tool_metadata_payload(registry.resolve(name or "", version))]
    except (OSError, AdapterError, ToolError) as error:
        payload = {
            "operation": f"TOOL {command.upper()}",
            "status": "FAIL",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        print(
            json.dumps(payload, indent=2)
            if as_json
            else f"TOOL {command.upper()}\nStatus: FAIL\nError: {error}"
        )
        return 2

    payload = {"operation": f"TOOL {command.upper()}", "status": "PASS", "tools": tools}
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"TOOL {command.upper()}")
        for item in tools:
            operations = ", ".join(operation["name"] for operation in item["operations"])
            print(f"{item['name']}@{item['version']}: {operations}")
        print("Status: PASS")
    return 0


def _adapter_metadata_payload(metadata: Any) -> dict[str, Any]:
    return {
        "name": metadata.name,
        "version": metadata.version,
        "operations": sorted(metadata.operations),
        "risk": metadata.risk.value,
        "side_effect": metadata.side_effect.value,
        "idempotent_operations": sorted(metadata.idempotent_operations),
    }


def _run_adapter_inspect(
    command: str,
    root: Path,
    *,
    name: str | None = None,
    version: str = "1",
    as_json: bool,
) -> int:
    try:
        registry = _core_adapter_registry(root)
        if command == "list":
            adapters = [_adapter_metadata_payload(item) for item in registry.list_metadata()]
        else:
            resolved = registry.resolve(name or "", version, "read_text")
            adapters = [_adapter_metadata_payload(resolved.metadata)]
    except (OSError, AdapterError) as error:
        payload = {
            "operation": f"ADAPTER {command.upper()}",
            "status": "FAIL",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        print(
            json.dumps(payload, indent=2)
            if as_json
            else f"ADAPTER {command.upper()}\nStatus: FAIL\nError: {error}"
        )
        return 2

    payload = {
        "operation": f"ADAPTER {command.upper()}",
        "status": "PASS",
        "adapters": adapters,
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"ADAPTER {command.upper()}")
        for item in adapters:
            print(
                f"{item['name']}@{item['version']}: "
                + ", ".join(item["operations"])
                + f" [{item['side_effect']}]"
            )
        print("Status: PASS")
    return 0


def _run_adapter_dry_run(
    name: str,
    version: str,
    root: Path,
    path: Path,
    task_id: str,
    *,
    as_json: bool,
) -> int:
    try:
        registry = _core_adapter_registry(root)
        requested = path.expanduser().resolve(strict=True)
        invocation = AdapterInvocation(
            invocation_id=f"dry-run-{task_id}",
            task_id=task_id,
            adapter=name,
            version=version,
            operation="read_text",
            agent_role=AgentRole.DEVELOPER,
            capability=Capability.IMPLEMENT,
            required_permission=Permission.MODIFY_CODE,
            inputs=(("path", str(requested)),),
        )
        task = Task(
            task_id=task_id,
            title="Adapter CLI dry-run",
            priority=Priority.P2,
            status=TaskStatus.IN_PROGRESS,
            agents=(AgentRole.DEVELOPER.value,),
            dependencies=(),
            acceptance_criteria=(AcceptanceCriterion("dry-run is governed"),),
        )
        result, audit = AdapterService(registry).execute(task, invocation)
        outputs = dict(result.outputs)
    except (OSError, AdapterError, TaskError) as error:
        payload = {
            "operation": "ADAPTER DRY-RUN",
            "status": "FAIL",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        print(
            json.dumps(payload, indent=2)
            if as_json
            else f"ADAPTER DRY-RUN\nStatus: FAIL\nError: {error}"
        )
        return 2

    payload = {
        "operation": "ADAPTER DRY-RUN",
        "status": "PASS",
        "adapter": f"{name}@{version}",
        "task_id": task_id,
        "path": outputs.get("path"),
        "content_bytes": len(outputs.get("content", "").encode()),
        "audit_sequence": audit.sequence,
        "content_returned": False,
    }
    print(
        json.dumps(payload, indent=2)
        if as_json
        else (
            "ADAPTER DRY-RUN\n"
            f"Adapter: {payload['adapter']}\n"
            f"Path: {payload['path']}\n"
            f"Bytes: {payload['content_bytes']}\n"
            "Content Returned: no\nStatus: PASS"
        )
    )
    return 0


def _workflow_registry() -> WorkflowRegistry:
    return WorkflowRegistry(core_workflows())


def _workflow_payload(definition: RuntimeWorkflowDefinition) -> dict[str, Any]:
    return {
        "name": definition.name,
        "version": definition.version,
        "description": definition.description,
        "driver": definition.driver,
        "max_steps": definition.max_steps,
        "max_fix_attempts": definition.max_fix_attempts,
        "approval_required": definition.approval_required,
        "required_output_sections": list(definition.required_output_sections),
        "stages": [
            {
                "name": stage.name,
                "agent_role": stage.agent_role.value,
                "capability": stage.capability.value,
                "required_permission": stage.required_permission.value,
            }
            for stage in definition.stages
        ],
    }


def _run_workflow_inspect(
    command: str,
    *,
    name: str | None = None,
    version: str = "1",
    as_json: bool,
) -> int:
    try:
        registry = _workflow_registry()
        definitions = (
            registry.list_definitions()
            if command == "list"
            else (registry.resolve(name or "", version),)
        )
        items = [_workflow_payload(item) for item in definitions]
    except WorkflowError as error:
        payload = {
            "operation": f"WORKFLOW {command.upper()}",
            "status": "FAIL",
            "error": str(error),
        }
        print(
            json.dumps(payload, indent=2)
            if as_json
            else f"WORKFLOW {command.upper()}\nStatus: FAIL\nError: {error}"
        )
        return 2
    payload = {"operation": f"WORKFLOW {command.upper()}", "status": "PASS", "workflows": items}
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"WORKFLOW {command.upper()}")
        for item in items:
            print(
                f"{item['name']}@{item['version']}: "
                + ", ".join(stage["name"] for stage in item["stages"])
            )
        print("Status: PASS")
    return 0


def _load_workflow_definition(path: Path) -> RuntimeWorkflowDefinition:
    payload = json.loads(path.expanduser().resolve(strict=True).read_text(encoding="utf-8"))
    stages = tuple(
        WorkflowStage(
            name=str(item["name"]),
            agent_role=AgentRole(str(item["agent_role"])),
            capability=Capability(str(item["capability"])),
            required_permission=Permission(str(item["required_permission"])),
        )
        for item in payload["stages"]
    )
    return RuntimeWorkflowDefinition(
        name=str(payload["name"]),
        version=str(payload["version"]),
        description=str(payload["description"]),
        driver=str(payload["driver"]),
        stages=stages,
        max_steps=int(payload["max_steps"]),
        max_fix_attempts=int(payload["max_fix_attempts"]),
        approval_required=bool(payload.get("approval_required", False)),
        required_output_sections=tuple(
            str(item) for item in payload.get("required_output_sections", ())
        ),
    )


def _run_workflow_validate(path: Path, *, as_json: bool) -> int:
    try:
        definition = _load_workflow_definition(path)
        validate_definition(definition)
    except (
        OSError,
        UnicodeError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        WorkflowError,
    ) as error:
        payload = {"operation": "WORKFLOW VALIDATE", "status": "FAIL", "error": str(error)}
        print(
            json.dumps(payload, indent=2)
            if as_json
            else f"WORKFLOW VALIDATE\nStatus: FAIL\nError: {error}"
        )
        return 2
    payload = {
        "operation": "WORKFLOW VALIDATE",
        "status": "PASS",
        "workflow": _workflow_payload(definition),
    }
    print(
        json.dumps(payload, indent=2)
        if as_json
        else f"WORKFLOW VALIDATE\n{definition.name}@{definition.version}\nStatus: PASS"
    )
    return 0


def _run_workflow_dry_run(
    name: str,
    version: str,
    task_id: str,
    objective: str,
    root: Path,
    store_path: Path | None,
    *,
    as_json: bool,
) -> int:
    try:
        control_plane = load_control_plane(root)
        task = _runtime_task(control_plane.tasks[task_id])
        dependencies = {
            dependency: TaskStatus(control_plane.tasks[dependency].status or "TODO")
            for dependency in task.dependencies
        }
        controller = ControllerEngine(AgentRuntime(AgentRouter(AgentRegistry(canonical_agents()))))
        store = JsonWorkflowStore(store_path or root / ".ai-os" / "workflows")
        engine = WorkflowEngine(_workflow_registry(), controller, store=store)
        session = engine.start(
            task,
            name,
            version,
            objective,
            dependency_states=dependencies,
            started_at=datetime.now(UTC),
            approval_evidence=("dry-run: no external side effects authorized",),
        )
    except (KeyError, OSError, ValueError, ControlPlaneError, TaskError, WorkflowError) as error:
        payload = {"operation": "WORKFLOW DRY-RUN", "status": "FAIL", "error": str(error)}
        print(
            json.dumps(payload, indent=2)
            if as_json
            else f"WORKFLOW DRY-RUN\nStatus: FAIL\nError: {error}"
        )
        return 2
    payload = {
        "operation": "WORKFLOW DRY-RUN",
        "status": "PASS",
        "session_id": session.session_id,
        "task_id": session.task_id,
        "workflow": f"{session.workflow}@{session.workflow_version}",
        "external_side_effects": False,
    }
    print(
        json.dumps(payload, indent=2)
        if as_json
        else f"WORKFLOW DRY-RUN\nSession: {session.session_id}\nStatus: PASS"
    )
    return 0


def _run_workflow_session(session_id: str, store_path: Path, *, as_json: bool) -> int:
    try:
        session = JsonWorkflowStore(store_path).get(session_id)
    except WorkflowError as error:
        payload = {"operation": "WORKFLOW SESSION", "status": "FAIL", "error": str(error)}
        print(
            json.dumps(payload, indent=2)
            if as_json
            else f"WORKFLOW SESSION\nStatus: FAIL\nError: {error}"
        )
        return 2
    payload = {
        "operation": "WORKFLOW SESSION",
        "status": "PASS",
        "session_id": session.session_id,
        "task_id": session.task_id,
        "workflow": f"{session.workflow}@{session.workflow_version}",
        "workflow_status": session.status.value,
        "events": len(session.events),
    }
    print(
        json.dumps(payload, indent=2)
        if as_json
        else f"WORKFLOW SESSION\nSession: {session.session_id}\nStatus: PASS"
    )
    return 0


def _store_status_payload(status: Any) -> dict[str, Any]:
    return {
        "database": str(status.database),
        "initialized": status.initialized,
        "schema_version": status.schema_version,
        "current_schema_version": status.current_schema_version,
        "records": {
            "controller_sessions": status.controller_sessions,
            "execution_plans": status.execution_plans,
            "execution_sessions": status.execution_sessions,
            "adapter_audit_events": status.adapter_audit_events,
            "runtime_events": status.runtime_events,
        },
    }


def _run_store(args: argparse.Namespace) -> int:
    try:
        store = SQLiteRuntimeStore(StoreConfig(database=args.database))
        if args.store_command == "init":
            payload = _store_status_payload(store.initialize())
        elif args.store_command == "migrate":
            payload = _store_status_payload(store.migrate())
        elif args.store_command == "status":
            payload = _store_status_payload(store.status())
        elif args.store_command == "session":
            controller_session = store.get_controller_session(args.session_id)
            payload = {
                "database": str(store.database),
                "session_id": controller_session.session_id,
                "task_id": controller_session.task_id,
                "stage": controller_session.stage.value,
                "task_status": controller_session.task_status.value,
                "outcome": (
                    controller_session.outcome.value if controller_session.outcome else None
                ),
                "events": len(controller_session.events),
                "updated_at": controller_session.updated_at.isoformat(),
            }
        elif args.store_command == "execution":
            execution_session = store.get_execution_session(args.execution_id)
            payload = {
                "database": str(store.database),
                "execution_id": execution_session.execution_id,
                "plan_id": execution_session.plan_id,
                "task_id": execution_session.task_id,
                "outcome": (execution_session.outcome.value if execution_session.outcome else None),
                "events": len(execution_session.events),
                "results": len(execution_session.results),
                "updated_at": execution_session.updated_at.isoformat(),
            }
        else:
            events = store.list_adapter_audit(
                invocation_id=args.invocation_id,
                limit=args.limit,
            )
            payload = {
                "database": str(store.database),
                "events": [
                    {
                        "sequence": event.sequence,
                        "invocation_id": event.invocation_id,
                        "task_id": event.task_id,
                        "adapter": event.adapter,
                        "operation": event.operation,
                        "timestamp": event.timestamp.isoformat(),
                        "status": event.status.value,
                        "evidence": list(event.evidence),
                    }
                    for event in events
                ],
            }
    except (OSError, PersistenceError) as error:
        failure = {
            "operation": "PERSISTENT RUNTIME STORE",
            "status": "FAIL",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        print(
            json.dumps(failure, indent=2)
            if args.json
            else f"PERSISTENT RUNTIME STORE\nStatus: FAIL\nError: {error}"
        )
        return 2
    result = {"operation": "PERSISTENT RUNTIME STORE", "status": "PASS", **payload}
    print(
        json.dumps(result, indent=2)
        if args.json
        else (
            "PERSISTENT RUNTIME STORE\n"
            f"Database: {store.database}\n"
            f"Command: {args.store_command}\nStatus: PASS"
        )
    )
    return 0


def _runtime_event_payload(event: Any) -> dict[str, Any]:
    return {
        "schema_version": event.schema_version,
        "event_id": event.event_id,
        "sequence": event.sequence,
        "timestamp": event.timestamp.isoformat(),
        "event_type": event.event_type.value,
        "source": event.source.value,
        "task_id": event.task_id,
        "trace_id": event.trace_id,
        "session_id": event.session_id,
        "workflow_session_id": event.workflow_session_id,
        "execution_id": event.execution_id,
        "invocation_id": event.invocation_id,
        "agent_role": event.agent_role,
        "summary": event.summary,
        "correlation": dict(event.correlation),
        "evidence": list(event.evidence),
    }


def _run_observability(args: argparse.Namespace) -> int:
    try:
        authorize_query(AuditQueryContext(AgentRole(args.actor_role), Permission.READ_CONTROL))
        store = SQLiteRuntimeStore(StoreConfig(database=args.database))
        events: tuple[RuntimeEvent, ...]
        if args.command == "audit" and args.audit_command == "show":
            events = (store.get_runtime_event(args.event_id),)
            operation = "RUNTIME AUDIT SHOW"
        else:
            filters = RuntimeEventFilter(
                task_id=getattr(args, "task_id", None),
                trace_id=(
                    args.trace_id if args.command == "trace" else getattr(args, "trace_id", None)
                ),
                execution_id=getattr(args, "execution_id", None),
                invocation_id=getattr(args, "invocation_id", None),
                event_type=(
                    RuntimeEventType(args.event_type) if getattr(args, "event_type", None) else None
                ),
                source=(RuntimeEventSource(args.source) if getattr(args, "source", None) else None),
            )
            events = store.list_runtime_events(filters=filters, limit=args.limit)
            operation = "RUNTIME TRACE SHOW" if args.command == "trace" else "RUNTIME AUDIT LIST"
            if args.command == "trace" and not events:
                raise PersistenceNotFoundError(f"unknown runtime trace: {args.trace_id}")
        payload = {
            "operation": operation,
            "status": "PASS",
            "database": str(store.database),
            "events": [_runtime_event_payload(event) for event in events],
        }
    except (OSError, PersistenceError, ObservabilityError) as error:
        payload = {
            "operation": "RUNTIME OBSERVABILITY",
            "status": "FAIL",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        print(
            json.dumps(payload, indent=2)
            if args.json
            else f"RUNTIME OBSERVABILITY\nStatus: FAIL\nError: {error}"
        )
        return 2
    print(json.dumps(payload, indent=2) if args.json else _human_runtime_events(operation, events))
    return 0


def _human_runtime_events(operation: str, events: tuple[RuntimeEvent, ...]) -> str:
    lines = [operation, f"Events: {len(events)}"]
    for event in events:
        lines.extend(
            (
                f"[{event.sequence}] {event.timestamp.isoformat()} "
                f"{event.source.value}/{event.event_type.value}",
                f"  Event: {event.event_id}",
                f"  Task: {event.task_id}  Trace: {event.trace_id}",
                f"  Summary: {event.summary}",
                f"  Correlation: {dict(event.correlation)}",
                f"  Evidence: {list(event.evidence)}",
            )
        )
    lines.append("Status: PASS")
    return "\n".join(lines)


def _run_monitoring(args: argparse.Namespace) -> int:
    payload: dict[str, Any]

    try:
        store = SQLiteRuntimeStore(StoreConfig(database=args.database))
        service = MonitoringService(store)
        context = MonitoringQueryContext(AgentRole(args.actor_role), Permission.READ_CONTROL)
        if args.command == "health":
            snapshot = service.health(
                context=context, stale_after=timedelta(seconds=args.stale_seconds)
            )
            payload = {
                "operation": "RUNTIME HEALTH",
                "status": "PASS",
                "health": snapshot.status.value,
                "checked_at": snapshot.checked_at.isoformat(),
                "checks": [
                    {
                        "component": check.component.value,
                        "status": check.status.value,
                        "summary": check.summary.value,
                    }
                    for check in snapshot.checks
                ],
            }
        else:
            points = service.metrics(context=context, window=timedelta(seconds=args.window_seconds))
            payload = {
                "operation": "RUNTIME METRICS",
                "status": "PASS",
                "metrics": [
                    {
                        "name": point.name,
                        "value": point.value,
                        "unit": point.unit,
                        "timestamp": point.timestamp.isoformat(),
                        "labels": dict(point.labels),
                    }
                    for point in points
                ],
            }
    except (OSError, PersistenceError, MonitoringError) as error:
        payload = {
            "operation": "RUNTIME MONITORING",
            "status": "FAIL",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        output = (
            json.dumps(payload, indent=2)
            if args.json
            else f"RUNTIME MONITORING\nStatus: FAIL\nError: {error}"
        )
        print(output)
        return 2
    if args.json:
        print(json.dumps(payload, indent=2))
    elif args.command == "health":
        lines = ["RUNTIME HEALTH", f"Status: {payload['health']}"]
        lines.extend(
            f"{check['component']}: {check['status']} ({check['summary']})"
            for check in payload["checks"]
        )
        print("\n".join(lines))
    else:
        lines = ["RUNTIME METRICS"]
        lines.extend(
            f"{point['name']}: {point['value']} {point['unit']}" for point in payload["metrics"]
        )
        lines.append("Status: PASS")
        print("\n".join(lines))
    return 0



def _run_config(args: argparse.Namespace) -> int:
    try:
        if args.config_command == "profiles":
            payload: dict[str, Any] = {
                "operation": "RUNTIME CONFIGURATION",
                "status": "PASS",
                "profiles": {
                    profile.value: defaults for profile, defaults in PROFILE_DEFAULTS.items()
                },
            }
        else:
            profile = EnvironmentProfile(args.profile)
            config = load_config_file(args.configuration, profile=profile)
            if args.config_command in {"show", "resolve"}:
                PermissionPolicy().require(AgentRole(args.actor_role), Permission.READ_CONTROL)
            payload = {
                "operation": "RUNTIME CONFIGURATION",
                "status": "PASS",
                "configuration": config.redacted(),
            }
            if args.config_command == "resolve":
                payload["dry_run"] = True
                payload["secret_references"] = [item.api_key.redacted for item in config.providers]
    except (OSError, ConfigurationError, ValueError) as error:
        payload = {
            "operation": "RUNTIME CONFIGURATION",
            "status": "FAIL",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        message = f"CONFIGURATION\nStatus: FAIL\nError: {error}"
        print(json.dumps(payload, indent=2) if args.json else message)
        return 2
    print(json.dumps(payload, indent=2) if args.json else _config_human(payload))
    return 0


def _config_human(payload: dict[str, Any]) -> str:
    if "profiles" in payload:
        return "RUNTIME CONFIGURATION PROFILES\n" + "\n".join(payload["profiles"])
    config = payload["configuration"]
    return "\n".join(
        [
            "RUNTIME CONFIGURATION",
            f"Profile: {config['environment']}",
            f"Database: {config['database_path']}",
            f"Providers: {len(config['providers'])}",
            "Status: PASS",
        ]
    )


def _run_secrets(args: argparse.Namespace) -> int:
    try:
        reference = SecretReference.parse(args.reference)
        service = SecretService(EnvironmentSecretProvider())
        present = service.check(
            reference,
            context=SecretAccessContext(AgentRole(args.actor_role), Permission.COORDINATE),
        )
        payload = {
            "operation": "SECRET CHECK",
            "status": "PASS" if present else "MISSING",
            "reference": reference.redacted,
            "present": present,
        }
    except (SecretError, ValueError) as error:
        payload = {
            "operation": "SECRET CHECK",
            "status": "FAIL",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        message = f"SECRET CHECK\nStatus: FAIL\nError: {error}"
        print(json.dumps(payload, indent=2) if args.json else message)
        return 2
    print(
        json.dumps(payload, indent=2)
        if args.json
        else f"SECRET CHECK\nReference: {reference.redacted}\nStatus: {payload['status']}"
    )
    return 0 if present else 1



def _scheduler_payload(record: Any) -> dict[str, Any]:
    return {
        "job_id": record.spec.job_id,
        "task_id": record.spec.task_id,
        "workflow": f"{record.spec.workflow_name}@{record.spec.workflow_version}",
        "kind": record.spec.kind.value,
        "state": record.state.value,
        "attempts": record.attempts,
        "next_run_at": record.next_run_at.isoformat(),
        "lease_owner": record.lease_owner,
        "lease_expires_at": (
            record.lease_expires_at.isoformat() if record.lease_expires_at else None
        ),
        "last_error": record.last_error,
    }


def _run_scheduler(args: argparse.Namespace) -> int:
    try:
        store = SQLiteSchedulerStore(StoreConfig(database=args.database))
        store.initialize()
        tasks = parse_tasks((args.root / "TASKS.md").read_text(encoding="utf-8"))
        approved_tasks = frozenset(
            task.task_id for task in tasks.values() if task.status in {"IN_PROGRESS", "REVIEW"}
        )
        definitions = core_workflows()
        service = SchedulerService(
            store,
            approved_tasks=approved_tasks,
            registered_workflows=frozenset((item.name, item.version) for item in definitions),
        )
        role = AgentRole(args.actor_role)
        command = args.scheduler_command
        if command == "create":
            interval = args.interval_seconds
            spec = JobSpec(
                job_id=args.job_id,
                task_id=args.task_id,
                workflow_name=args.workflow,
                workflow_version=args.version,
                run_at=datetime.fromisoformat(args.run_at),
                kind=ScheduleKind.INTERVAL if interval is not None else ScheduleKind.ONCE,
                interval_seconds=interval,
                max_attempts=args.max_attempts,
                retry_backoff_seconds=args.retry_backoff_seconds,
                timeout_seconds=args.timeout_seconds,
                max_elapsed_seconds=args.max_elapsed_seconds,
                jitter_seconds=args.jitter_seconds,
            )
            record = service.create(spec, context=SchedulerContext(role, Permission.COORDINATE))
            payload: dict[str, Any] = {
                "operation": "SCHEDULER CREATE",
                "status": "PASS",
                "job": _scheduler_payload(record),
            }
        elif command == "list":
            records = service.list(
                context=SchedulerContext(role, Permission.READ_CONTROL), limit=args.limit
            )
            payload = {
                "operation": "SCHEDULER LIST",
                "status": "PASS",
                "jobs": [_scheduler_payload(record) for record in records],
            }
        elif command == "show":
            record = service.get(
                args.job_id, context=SchedulerContext(role, Permission.READ_CONTROL)
            )
            payload = {
                "operation": "SCHEDULER SHOW",
                "status": "PASS",
                "job": _scheduler_payload(record),
            }
        elif command == "cancel":
            record = service.cancel(
                args.job_id, context=SchedulerContext(role, Permission.COORDINATE)
            )
            payload = {
                "operation": "SCHEDULER CANCEL",
                "status": "PASS",
                "job": _scheduler_payload(record),
            }
        else:
            records = service.list(
                context=SchedulerContext(role, Permission.READ_CONTROL), limit=args.limit
            )
            now = datetime.now(UTC)
            due = next(
                (
                    record
                    for record in records
                    if record.state.value in {"SCHEDULED", "RETRY_WAIT"}
                    and record.next_run_at <= now
                ),
                None,
            )
            payload = {
                "operation": "SCHEDULER CLAIM DRY RUN",
                "status": "PASS",
                "worker_id": args.worker_id,
                "would_claim": _scheduler_payload(due) if due else None,
                "external_side_effects": False,
            }
    except (OSError, ValueError, ControlPlaneError, PersistenceError, SchedulerError) as error:
        payload = {
            "operation": "SCHEDULER",
            "status": "FAIL",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        output = (
            json.dumps(payload, indent=2)
            if args.json
            else f"SCHEDULER\nStatus: FAIL\nError: {error}"
        )
        print(output)
        return 2
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(payload["operation"])
        if "job" in payload:
            job = payload["job"]
            print(f"{job['job_id']}: {job['state']} ({job['workflow']})")
        elif "jobs" in payload:
            for job in payload["jobs"]:
                print(f"{job['job_id']}: {job['state']} ({job['workflow']})")
        else:
            job = payload["would_claim"]
            print(f"Would claim: {job['job_id'] if job else 'none'}")
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

    if args.command == "adapter" and args.adapter_command in {"list", "describe", "validate"}:
        return _run_adapter_inspect(
            args.adapter_command,
            args.root,
            name=getattr(args, "name", None),
            version=getattr(args, "version", "1"),
            as_json=args.json,
        )

    if args.command == "adapter" and args.adapter_command == "dry-run":
        return _run_adapter_dry_run(
            args.name,
            args.version,
            args.root,
            args.path,
            args.task_id,
            as_json=args.json,
        )

    if args.command == "tool" and args.tool_command in {"list", "describe", "validate"}:
        return _run_tool_inspect(
            args.tool_command,
            args.root,
            name=getattr(args, "name", None),
            version=getattr(args, "version", "1"),
            as_json=args.json,
        )

    if args.command == "workflow" and args.workflow_command in {"list", "describe"}:
        return _run_workflow_inspect(
            args.workflow_command,
            name=getattr(args, "name", None),
            version=getattr(args, "version", "1"),
            as_json=args.json,
        )

    if args.command == "workflow" and args.workflow_command == "validate":
        return _run_workflow_validate(args.definition, as_json=args.json)

    if args.command == "workflow" and args.workflow_command == "dry-run":
        return _run_workflow_dry_run(
            args.name,
            args.version,
            args.task_id,
            args.objective,
            args.root,
            args.store,
            as_json=args.json,
        )

    if args.command == "workflow" and args.workflow_command == "session":
        return _run_workflow_session(args.session_id, args.store, as_json=args.json)

    if args.command == "store":
        return _run_store(args)

    if args.command in {"audit", "trace"}:
        return _run_observability(args)

    if args.command in {"health", "metrics"}:
        return _run_monitoring(args)


    if args.command == "config":
        return _run_config(args)

    if args.command == "secrets":
        return _run_secrets(args)


    if args.command == "scheduler":
        return _run_scheduler(args)

    parser.error("Unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
