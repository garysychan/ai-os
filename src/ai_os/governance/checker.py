"""CP-C01 through CP-C10 Control Plane consistency checks."""

from __future__ import annotations

import re
from collections.abc import Callable

from .findings import ConsistencyReport, Finding, Severity
from .loader import REQUIRED_FILES, VALID_TASK_STATES
from .models import ControlPlane
from .permissions import check_permissions
from .references import check_document_references
from .versions import check_versions

Check = Callable[[ControlPlane], list[Finding]]
_RULE_ID_RE = re.compile(r"\\b(RULE-[A-Z]+-\\d+)\\b")
_RESPONSIBLE_RE = re.compile(
    r"^Responsible:\\s*(.+?)\\s*$",
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
    findings = check_document_references(control_plane.documents)
    known_agents = {name.casefold() for name in control_plane.agents}
    workflow = control_plane.documents["WORKFLOW.md"]

    for value in _RESPONSIBLE_RE.findall(workflow):
        for candidate in re.split(r"\\s*/\\s*", value):
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
    if not workflow.transitions:
        findings.append(
            _finding(
                "CP-C04",
                Severity.WARNING,
                "WORKFLOW.md",
                "No explicit state transitions were parsed",
                remediation="Declare executable state transitions",
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
    architecture = control_plane.documents["ARCHITECTURE.md"].casefold()
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
    for rule in control_plane.rules.values():
        normalized = re.sub(r"\\W+", " ", rule.text).strip().casefold()
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
    return findings
