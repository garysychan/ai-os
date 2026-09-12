"""CP-C01 through CP-C10 Control Plane consistency checks."""

from __future__ import annotations

import re
from collections.abc import Callable

from .findings import ConsistencyReport, Finding, Severity
from .loader import REQUIRED_FILES, VALID_TASK_STATES
from .models import ControlPlane
from .permissions import check_permissions
from .references import check_document_references
from .transitions import ALLOWED_TRANSITIONS, is_valid_transition
from .versions import check_versions

Check = Callable[[ControlPlane], list[Finding]]
_RULE_ID_RE = re.compile(r"\b(RULE-[A-Z]+-\d+)\b")
_RESPONSIBLE_RE = re.compile(
    r"^Responsible:\s*(.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def run_consistency_checks(control_plane: ControlPlane) -> ConsistencyReport:
    """Run every registered consistency check in stable check-ID order."""
    checks: tuple[Check, ...] = (
        _check_required_files,
        _check_references,
        _check_agents,
        _check_workflow,
        _check_architecture,
        _check_rules,
        _check_tasks,
        _check_permission_model,
        _check_version_model,
        _check_orphans,
    )
    findings = [finding for check in checks for finding in check(control_plane)]
    findings.sort(
        key=lambda item: (
            item.check_id,
            -int(item.severity),
            item.document,
            item.subject or "",
            item.message,
        )
    )
    return ConsistencyReport(tuple(findings))


def _finding(
    check_id: str,
    severity: Severity,
    document: str,
    message: str,
    *,
    subject: str | None = None,
    evidence: str | None = None,
    remediation: str | None = None,
) -> Finding:
    return Finding(
        check_id=check_id,
        severity=severity,
        document=document,
        subject=subject,
        message=message,
        evidence=evidence,
        remediation=remediation,
    )


def _check_required_files(control_plane: ControlPlane) -> list[Finding]:
    missing = sorted(set(REQUIRED_FILES) - set(control_plane.documents))
    return [
        _finding(
            "CP-C01",
            Severity.FAIL,
            name,
            "Required Control Plane document is not loaded",
            remediation="Restore the document and rerun bootstrap",
        )
        for name in missing
    ]


def _check_references(control_plane: ControlPlane) -> list[Finding]:
    findings = check_document_references(
        control_plane.documents,
        control_plane.root,
    )
    known_agents = {name.casefold() for name in control_plane.agents}
    workflow = control_plane.documents["WORKFLOW.md"]

    for value in _RESPONSIBLE_RE.findall(workflow):
        for candidate in re.split(r"\s*/\s*", value):
            name = candidate.strip()
            if (
                not name
                or name.casefold() in known_agents
                or name.casefold() == "relevant specialist"
            ):
                continue
            findings.append(
                _finding(
                    "CP-C02",
                    Severity.FAIL,
                    "WORKFLOW.md",
                    "Workflow references an undefined responsible Agent",
                    subject=name,
                    evidence=value,
                    remediation="Define the Agent or correct the workflow reference",
                )
            )
    return findings


def _check_agents(control_plane: ControlPlane) -> list[Finding]:
    findings: list[Finding] = []
    responsibility_owners: dict[str, list[str]] = {}

    for agent in control_plane.agents.values():
        if not agent.responsibilities:
            findings.append(
                _finding(
                    "CP-C03",
                    Severity.WARNING,
                    "AGENTS.md",
                    "Agent has no parsed responsibilities",
                    subject=agent.name,
                    remediation="Add a Responsibilities list",
                )
            )
        for responsibility in agent.responsibilities:
            normalized = re.sub(
                r"\W+", " ", responsibility
            ).strip().casefold()
            responsibility_owners.setdefault(normalized, []).append(agent.name)

    for responsibility, owners in responsibility_owners.items():
        if responsibility and len(owners) > 1:
            findings.append(
                _finding(
                    "CP-C03",
                    Severity.WARNING,
                    "AGENTS.md",
                    "Responsibility is assigned identically to multiple Agents",
                    subject=", ".join(sorted(owners)),
                    evidence=responsibility,
                    remediation="Clarify ownership or explicitly document shared responsibility",
                )
            )

    permission_markdown = control_plane.documents["AGENTS.md"]
    table_agents = {
        name.casefold()
        for name in re.findall(
            r"^\|\s*([A-Za-z][A-Za-z ]+?)\s*\|",
            permission_markdown,
            re.MULTILINE,
        )
        if name.casefold() not in {"agent", "actor"}
    }
    defined_agents = {name.casefold() for name in control_plane.agents}
    for name in sorted(table_agents - defined_agents):
        findings.append(
            _finding(
                "CP-C03",
                Severity.FAIL,
                "AGENTS.md",
                "Permission table references an undefined Agent",
                subject=name,
                remediation="Define the Agent or remove the permission row",
            )
        )
    for name in sorted(defined_agents - table_agents):
        findings.append(
            _finding(
                "CP-C03",
                Severity.WARNING,
                "AGENTS.md",
                "Defined Agent has no permission-table row",
                subject=name,
                remediation="Declare explicit permissions for the Agent",
            )
        )
    return findings

def _check_workflow(control_plane: ControlPlane) -> list[Finding]:
    findings: list[Finding] = []
    workflow = control_plane.workflow
    for state in sorted(VALID_TASK_STATES - workflow.states):
        findings.append(
            _finding(
                "CP-C04",
                Severity.FAIL,
                "WORKFLOW.md",
                "Required workflow state is missing",
                subject=state,
                remediation="Define the state in State Model",
            )
        )
    for source, target in workflow.transitions:
        for state in (source, target):
            if state not in workflow.states:
                findings.append(
                    _finding(
                        "CP-C04",
                        Severity.FAIL,
                        "WORKFLOW.md",
                        "Transition references an undefined state",
                        subject=state,
                        evidence=f"{source} -> {target}",
                        remediation="Define the state or remove the transition",
                    )
                )
        if not is_valid_transition(source, target):
            findings.append(
                _finding(
                    "CP-C04",
                    Severity.FAIL,
                    "WORKFLOW.md",
                    "Transition violates the executable transition policy",
                    subject=f"{source} -> {target}",
                    remediation="Use an allowed transition or approve a policy change",
                )
            )
    if not workflow.transitions:
        findings.append(
            _finding(
                "CP-C04",
                Severity.WARNING,
                "WORKFLOW.md",
                "No explicit state transitions were parsed",
                evidence=", ".join(
                    f"{source}->{target}"
                    for source, target in sorted(ALLOWED_TRANSITIONS)
                ),
                remediation="Declare executable transitions in WORKFLOW.md",
            )
        )
    if not workflow.stages:
        findings.append(
            _finding(
                "CP-C04",
                Severity.FAIL,
                "WORKFLOW.md",
                "No executable workflow stages were parsed",
                remediation="Define Stage headings",
            )
        )
    return findings

def _check_architecture(control_plane: ControlPlane) -> list[Finding]:
    markdown = control_plane.documents["ARCHITECTURE.md"]
    architecture = markdown.casefold()
    findings: list[Finding] = []
    required_concepts = {
        "control plane": "Document the Control Plane boundary",
        "workflow": "Document the workflow/runtime boundary",
        "testing": "Document the validation/testing architecture",
        "security": "Document the security architecture",
    }
    for concept, remediation in required_concepts.items():
        if concept not in architecture:
            findings.append(
                _finding(
                    "CP-C05",
                    Severity.WARNING,
                    "ARCHITECTURE.md",
                    "Required architecture concept is not documented",
                    subject=concept,
                    remediation=remediation,
                )
            )

    architecture_states = set(
        re.findall(
            r"\b(TODO|IN_PROGRESS|BLOCKED|REVIEW|DONE)\b",
            markdown,
        )
    )
    if architecture_states and architecture_states != set(
        control_plane.workflow.states
    ):
        findings.append(
            _finding(
                "CP-C05",
                Severity.FAIL,
                "ARCHITECTURE.md",
                "Architecture and Workflow define different task states",
                evidence=(
                    f"architecture={sorted(architecture_states)}; "
                    f"workflow={sorted(control_plane.workflow.states)}"
                ),
                remediation="Reconcile ARCHITECTURE.md with WORKFLOW.md",
            )
        )

    architecture_agents = {
        name
        for name in control_plane.agents
        if re.search(rf"\b{re.escape(name)}\b", markdown)
    }
    workflow_agents = {
        name
        for name in control_plane.agents
        if re.search(
            rf"\b{re.escape(name)}\b",
            control_plane.documents["WORKFLOW.md"],
        )
    }
    for name in sorted(workflow_agents - architecture_agents):
        findings.append(
            _finding(
                "CP-C05",
                Severity.WARNING,
                "ARCHITECTURE.md",
                "Workflow Agent is absent from the logical architecture",
                subject=name,
                remediation="Document the Agent or revise the workflow assignment",
            )
        )
    return findings

def _check_rules(control_plane: ControlPlane) -> list[Finding]:
    markdown = control_plane.documents["PROJECT_RULES.md"]
    findings: list[Finding] = []
    seen: set[str] = set()
    for rule_id in _RULE_ID_RE.findall(markdown):
        if rule_id in seen:
            findings.append(
                _finding(
                    "CP-C06",
                    Severity.FAIL,
                    "PROJECT_RULES.md",
                    "Duplicate rule identifier",
                    subject=rule_id,
                    remediation="Assign a unique Rule ID",
                )
            )
        seen.add(rule_id)

    by_text: dict[str, str] = {}
    polarity: dict[str, tuple[str, bool]] = {}
    negation = re.compile(r"\b(?:not|never|cannot|must not|do not)\b")
    for rule in control_plane.rules.values():
        normalized = re.sub(r"\W+", " ", rule.text).strip().casefold()
        previous = by_text.get(normalized)
        if previous and previous != rule.rule_id:
            findings.append(
                _finding(
                    "CP-C06",
                    Severity.WARNING,
                    "PROJECT_RULES.md",
                    "Rules have duplicate normalized text",
                    subject=rule.rule_id,
                    evidence=previous,
                    remediation="Consolidate or distinguish the rules",
                )
            )
        by_text[normalized] = rule.rule_id

        is_negative = bool(negation.search(normalized))
        proposition = negation.sub("", normalized)
        proposition = re.sub(r"\s+", " ", proposition).strip()
        prior = polarity.get(proposition)
        if prior and prior[1] != is_negative:
            findings.append(
                _finding(
                    "CP-C06",
                    Severity.FAIL,
                    "PROJECT_RULES.md",
                    "Rules contain opposite structured propositions",
                    subject=rule.rule_id,
                    evidence=prior[0],
                    remediation="Resolve the conflict through Change Control",
                )
            )
        else:
            polarity[proposition] = (rule.rule_id, is_negative)
    return findings

def _check_tasks(control_plane: ControlPlane) -> list[Finding]:
    findings: list[Finding] = []
    known_agents = {name.casefold() for name in control_plane.agents}
    task_ids = set(control_plane.tasks)

    for task in control_plane.tasks.values():
        if task.status not in VALID_TASK_STATES:
            findings.append(
                _finding(
                    "CP-C07",
                    Severity.FAIL,
                    "TASKS.md",
                    "Task has missing or invalid state",
                    subject=task.task_id,
                    evidence=task.status,
                    remediation="Use an allowed workflow state",
                )
            )
        for agent in task.agents:
            if agent.casefold() not in known_agents:
                findings.append(
                    _finding(
                        "CP-C07",
                        Severity.FAIL,
                        "TASKS.md",
                        "Task references an undefined Agent",
                        subject=task.task_id,
                        evidence=agent,
                        remediation="Define the Agent or correct the assignment",
                    )
                )
        for dependency in task.dependencies:
            if dependency not in task_ids:
                findings.append(
                    _finding(
                        "CP-C07",
                        Severity.FAIL,
                        "TASKS.md",
                        "Task references an undefined dependency",
                        subject=task.task_id,
                        evidence=dependency,
                        remediation="Define or remove the dependency",
                    )
                )
        if not task.acceptance_criteria:
            findings.append(
                _finding(
                    "CP-C07",
                    Severity.WARNING,
                    "TASKS.md",
                    "Executable task has no acceptance criteria",
                    subject=task.task_id,
                    remediation="Add measurable acceptance criteria",
                )
            )

    for cycle in _dependency_cycles(control_plane):
        findings.append(
            _finding(
                "CP-C07",
                Severity.FAIL,
                "TASKS.md",
                "Task dependency cycle detected",
                subject=cycle[0],
                evidence=" -> ".join(cycle),
                remediation="Remove at least one dependency in the cycle",
            )
        )
    return findings


def _dependency_cycles(control_plane: ControlPlane) -> list[tuple[str, ...]]:
    graph = {
        task_id: tuple(
            dependency
            for dependency in task.dependencies
            if dependency in control_plane.tasks
        )
        for task_id, task in control_plane.tasks.items()
    }
    visiting: list[str] = []
    visited: set[str] = set()
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        if node in visiting:
            start = visiting.index(node)
            raw = visiting[start:] + [node]
            body = raw[:-1]
            rotations = [
                tuple(body[index:] + body[:index] + [body[index]])
                for index in range(len(body))
            ]
            cycles.add(min(rotations))
            return
        if node in visited:
            return
        visiting.append(node)
        for dependency in graph[node]:
            visit(dependency)
        visiting.pop()
        visited.add(node)

    for task_id in sorted(graph):
        visit(task_id)
    return sorted(cycles)


def _check_permission_model(control_plane: ControlPlane) -> list[Finding]:
    return check_permissions(control_plane.documents)


def _check_version_model(control_plane: ControlPlane) -> list[Finding]:
    return check_versions(control_plane.documents)


def _check_orphans(control_plane: ControlPlane) -> list[Finding]:
    findings: list[Finding] = []
    authoritative = {
        entry.document for entry in control_plane.authority_map.values()
    }
    for document in REQUIRED_FILES:
        if document == "CONTROL_PLANE.md":
            continue
        if document not in authoritative:
            findings.append(
                _finding(
                    "CP-C10",
                    Severity.WARNING,
                    "CONTROL_PLANE.md",
                    "Controlled document has no authority-map designation",
                    subject=document,
                    remediation="Add the document to the Authority Model",
                )
            )

    referenced_agents = {
        agent.casefold()
        for task in control_plane.tasks.values()
        for agent in task.agents
    }
    workflow_markdown = control_plane.documents["WORKFLOW.md"].casefold()
    for name in sorted(control_plane.agents):
        if (
            name.casefold() not in referenced_agents
            and re.search(rf"\b{re.escape(name.casefold())}\b", workflow_markdown)
            is None
        ):
            findings.append(
                _finding(
                    "CP-C10",
                    Severity.WARNING,
                    "AGENTS.md",
                    "Agent is not referenced by Workflow or Tasks",
                    subject=name,
                    remediation="Assign the Agent or remove the orphan definition",
                )
            )

    used_states = {
        state
        for transition in control_plane.workflow.transitions
        for state in transition
    } | {
        task.status
        for task in control_plane.tasks.values()
        if task.status is not None
    }
    for state in sorted(control_plane.workflow.states - used_states):
        findings.append(
            _finding(
                "CP-C10",
                Severity.WARNING,
                "WORKFLOW.md",
                "Workflow state is not used by a Task or explicit transition",
                subject=state,
                remediation="Use the state or document why it is reserved",
            )
        )
    return findings

def _check_orphans(control_plane: ControlPlane) -> list[Finding]:
    findings: list[Finding] = []
    authoritative = {
        entry.document for entry in control_plane.authority_map.values()
    }
    for document in REQUIRED_FILES:
        if document == "CONTROL_PLANE.md":
            continue
        if document not in authoritative:
            findings.append(
                _finding(
                    "CP-C10",
                    Severity.WARNING,
                    "CONTROL_PLANE.md",
                    "Controlled document has no authority-map designation",
                    subject=document,
                    remediation="Add the document to the Authority Model",
                )
            )
    return findings
