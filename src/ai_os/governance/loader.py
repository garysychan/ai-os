"""Load and parse the six Markdown documents that govern AI OS.

The parser targets the stable structures in the repository: Markdown headings,
labelled task fields, rule identifiers, workflow states and the authority table
in CONTROL_PLANE.md. It is intentionally not a general-purpose Markdown parser.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Mapping

from .errors import ControlPlaneParseError, MissingControlPlaneFileError
from .models import (
    AgentDefinition,
    AuthorityEntry,
    ControlPlane,
    RuleDefinition,
    TaskDefinition,
    WorkflowDefinition,
)

REQUIRED_FILES = (
    "CONTROL_PLANE.md",
    "AGENTS.md",
    "PROJECT_RULES.md",
    "ARCHITECTURE.md",
    "WORKFLOW.md",
    "TASKS.md",
)

VALID_TASK_STATES = frozenset(
    {"TODO", "IN_PROGRESS", "BLOCKED", "REVIEW", "DONE"}
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_RULE_RE = re.compile(
    r"^\s*-\s+\*\*(RULE-[A-Z]+-\d+):\*\*\s*(.+?)\s*$",
    re.MULTILINE,
)
_TASK_RE = re.compile(
    r"^##\s+(TASK-\d+)\s+[—-]\s+(.+?)\s*$\n"
    r"(.*?)(?=^##\s+TASK-\d+\s+[—-]|\Z)",
    re.MULTILINE | re.DOTALL,
)
_FIELD_RE_TEMPLATE = r"^\s*{name}:\s*(.+?)\s*$"
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")


def validate_required_files(root: str | Path) -> dict[str, Path]:
    """Return required-file paths or raise with the complete missing set."""
    control_root = Path(root).expanduser().resolve()
    if not control_root.is_dir():
        raise MissingControlPlaneFileError(
            f"Control Plane root is not a directory: {control_root}"
        )

    paths = {name: control_root / name for name in REQUIRED_FILES}
    missing = [name for name, path in paths.items() if not path.is_file()]
    unreadable = [
        name
        for name, path in paths.items()
        if path.is_file() and not _is_readable(path)
    ]

    if missing or unreadable:
        details = []
        if missing:
            details.append("missing=" + ", ".join(missing))
        if unreadable:
            details.append("unreadable=" + ", ".join(unreadable))
        raise MissingControlPlaneFileError(
            "Required Control Plane validation failed: " + "; ".join(details)
        )
    return paths


def load_control_plane(root: str | Path) -> ControlPlane:
    """Load, parse and minimally cross-validate all six documents."""
    paths = validate_required_files(root)
    documents = {
        name: path.read_text(encoding="utf-8") for name, path in paths.items()
    }

    agents = parse_agent_definitions(documents["AGENTS.md"])
    rules = parse_rules(documents["PROJECT_RULES.md"])
    workflow = parse_workflow(documents["WORKFLOW.md"])
    tasks = parse_tasks(documents["TASKS.md"])
    authority_map = build_authority_map(documents["CONTROL_PLANE.md"])
    warnings = _cross_validate(agents, workflow, tasks, authority_map)

    return ControlPlane(
        root=Path(root).expanduser().resolve(),
        documents=documents,
        agents=agents,
        rules=rules,
        workflow=workflow,
        tasks=tasks,
        authority_map=authority_map,
        warnings=tuple(warnings),
    )


def parse_agent_definitions(
    markdown: str,
) -> dict[str, AgentDefinition]:
    """Parse role sections below the Agent Hierarchy heading."""
    hierarchy = _section(markdown, "Agent Hierarchy", level=2)
    role_sections = _child_sections(hierarchy, level=3)
    agents: dict[str, AgentDefinition] = {}

    for name, body in role_sections:
        clean_name = re.sub(
            r"^\d+(?:\.\d+)*\.?\s*", "", name
        ).strip()
        responsibilities = _bullets_after_label(
            body, "Responsibilities"
        )
        restrictions = _bullets_after_label(body, "Cannot")
        agents[clean_name] = AgentDefinition(
            name=clean_name,
            responsibilities=tuple(responsibilities),
            restrictions=tuple(restrictions),
        )

    if not agents:
        raise ControlPlaneParseError(
            "AGENTS.md contains no roles under 'Agent Hierarchy'"
        )
    return agents


def parse_rules(markdown: str) -> dict[str, RuleDefinition]:
    """Parse RULE-CATEGORY-NNN entries from PROJECT_RULES.md."""
    rules: dict[str, RuleDefinition] = {}
    for match in _RULE_RE.finditer(markdown):
        rule_id, text = match.groups()
        category = rule_id.split("-")[1]
        if rule_id in rules:
            raise ControlPlaneParseError(
                f"Duplicate rule ID: {rule_id}"
            )
        rules[rule_id] = RuleDefinition(
            rule_id=rule_id,
            text=text.strip(),
            category=category,
        )
    if not rules:
        raise ControlPlaneParseError(
            "PROJECT_RULES.md contains no RULE-* definitions"
        )
    return rules


def parse_workflow(markdown: str) -> WorkflowDefinition:
    """Parse stage names, task states and explicit transitions."""
    state_section = _section(markdown, "State Model", level=2)
    states = frozenset(
        re.findall(
            r"\`(TODO|IN_PROGRESS|BLOCKED|REVIEW|DONE)\`",
            state_section,
        )
    )
    if not states:
        raise ControlPlaneParseError(
            "WORKFLOW.md contains no allowed task states"
        )

    stages = []
    for heading in _headings(markdown, level=3):
        match = re.match(
            r"Stage\s+\d+\s+[—-]\s+(.+)",
            heading,
            re.IGNORECASE,
        )
        if match:
            stages.append(
                match.group(1).strip().upper().replace(" ", "_")
            )
    if not stages:
        raise ControlPlaneParseError(
            "WORKFLOW.md contains no Stage definitions"
        )

    transitions = tuple(
        (source, target)
        for source, target in re.findall(
            r"\b(TODO|IN_PROGRESS|BLOCKED|REVIEW|DONE)\s*"
            r"(?:→|->)\s*"
            r"(TODO|IN_PROGRESS|BLOCKED|REVIEW|DONE)\b",
            markdown,
        )
    )
    return WorkflowDefinition(
        stages=tuple(stages),
        states=states,
        transitions=transitions,
    )


def parse_tasks(markdown: str) -> dict[str, TaskDefinition]:
    """Parse executable TASK-* sections from TASKS.md."""
    tasks: dict[str, TaskDefinition] = {}
    for match in _TASK_RE.finditer(markdown):
        task_id, title, body = match.groups()
        status = _field(body, "Status")
        priority = _field(body, "Priority")
        agent_value = _field(body, "Agent") or ""
        dependency_value = _field(body, "Dependencies") or ""

        agents = tuple(
            item.strip()
            for item in re.split(r"/|,", agent_value)
            if item.strip()
        )
        dependencies = (
            ()
            if dependency_value.lower() == "none"
            else tuple(re.findall(r"TASK-\d+", dependency_value))
        )
        acceptance = tuple(
            _checklist_items(
                _subsection(body, "Acceptance Criteria")
            )
        )

        if status and status not in VALID_TASK_STATES:
            raise ControlPlaneParseError(
                f"{task_id} has invalid state: {status}"
            )
        if task_id in tasks:
            raise ControlPlaneParseError(
                f"Duplicate task ID: {task_id}"
            )

        tasks[task_id] = TaskDefinition(
            task_id=task_id,
            title=title.strip(),
            status=status,
            priority=priority,
            agents=agents,
            dependencies=dependencies,
            acceptance_criteria=acceptance,
        )
    if not tasks:
        raise ControlPlaneParseError(
            "TASKS.md contains no TASK-* definitions"
        )
    return tasks


def build_authority_map(
    markdown: str,
) -> dict[str, AuthorityEntry]:
    """Build domain-to-document mappings from CONTROL_PLANE.md."""
    section = _section(markdown, "Authority Model", level=2)
    authority: dict[str, AuthorityEntry] = {}

    for line in section.splitlines():
        match = _TABLE_ROW_RE.match(line.strip())
        if not match:
            continue
        cells = [
            re.sub(r"[`*]", "", cell).strip()
            for cell in match.group(1).split("|")
        ]
        if len(cells) != 2:
            continue
        if cells[0].lower() == "decision domain":
            continue
        if cells[0] and set(cells[0]) == {"-"}:
            continue

        domain, document = cells
        authority[domain] = AuthorityEntry(
            domain=domain,
            document=document,
        )

    if not authority:
        raise ControlPlaneParseError(
            "CONTROL_PLANE.md has no authority table"
        )
    return authority


def _cross_validate(
    agents: Mapping[str, AgentDefinition],
    workflow: WorkflowDefinition,
    tasks: Mapping[str, TaskDefinition],
    authority_map: Mapping[str, AuthorityEntry],
) -> list[str]:
    """Return non-blocking cross-document validation findings."""
    warnings: list[str] = []
    known_agents = {name.casefold() for name in agents}

    for task in tasks.values():
        for agent in task.agents:
            if agent.casefold() not in known_agents:
                warnings.append(
                    f"{task.task_id} references undefined agent: {agent}"
                )
        for dependency in task.dependencies:
            if dependency not in tasks:
                warnings.append(
                    f"{task.task_id} references undefined dependency: "
                    f"{dependency}"
                )
        if not task.acceptance_criteria:
            warnings.append(
                f"{task.task_id} has no acceptance criteria"
            )

    missing_states = VALID_TASK_STATES - workflow.states
    if missing_states:
        warnings.append(
            "Workflow omits expected states: "
            + ", ".join(sorted(missing_states))
        )

    authoritative_docs = {
        entry.document for entry in authority_map.values()
    }
    for expected in REQUIRED_FILES:
        if (
            expected not in authoritative_docs
            and expected != "CONTROL_PLANE.md"
        ):
            warnings.append(
                f"Authority map does not designate {expected}"
            )
    return warnings


def _is_readable(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8") as stream:
            stream.read(1)
        return True
    except (OSError, UnicodeError):
        return False


def _headings(markdown: str, level: int) -> Iterable[str]:
    for match in _HEADING_RE.finditer(markdown):
        if len(match.group(1)) == level:
            yield match.group(2).strip()


def _section(markdown: str, title: str, level: int) -> str:
    headings = list(_HEADING_RE.finditer(markdown))
    wanted = title.casefold()

    for index, match in enumerate(headings):
        heading_level = len(match.group(1))
        heading_title = re.sub(
            r"^\d+(?:\.\d+)*\.?\s*",
            "",
            match.group(2),
        ).strip()
        if (
            heading_level != level
            or heading_title.casefold() != wanted
        ):
            continue

        end = len(markdown)
        for later in headings[index + 1 :]:
            if len(later.group(1)) <= level:
                end = later.start()
                break
        return markdown[match.end() : end]

    raise ControlPlaneParseError(
        f"Missing level-{level} section: {title}"
    )


def _child_sections(
    markdown: str,
    level: int,
) -> list[tuple[str, str]]:
    matches = [
        match
        for match in _HEADING_RE.finditer(markdown)
        if len(match.group(1)) == level
    ]
    result = []

    for index, match in enumerate(matches):
        end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(markdown)
        )
        result.append(
            (
                match.group(2).strip(),
                markdown[match.end() : end],
            )
        )
    return result


def _bullets_after_label(
    body: str,
    label: str,
) -> list[str]:
    pattern = re.compile(
        rf"^\s*{re.escape(label)}:\s*$\n"
        rf"((?:\s*-\s+.+\n?)+)",
        re.MULTILINE | re.IGNORECASE,
    )
    match = pattern.search(body)
    if not match:
        return []
    return re.findall(
        r"^\s*-\s+(.+?)\s*$",
        match.group(1),
        re.MULTILINE,
    )


def _field(body: str, name: str) -> str | None:
    match = re.search(
        _FIELD_RE_TEMPLATE.format(name=re.escape(name)),
        body,
        re.MULTILINE | re.IGNORECASE,
    )
    return match.group(1).strip().strip("*`") if match else None


def _subsection(body: str, name: str) -> str:
    match = re.search(
        rf"^\s*{re.escape(name)}:\s*$\n"
        rf"(.*?)(?=^\s*[A-Za-z][A-Za-z ]+:\s*$|\Z)",
        body,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    return match.group(1) if match else ""


def _checklist_items(body: str) -> Iterable[str]:
    for match in re.finditer(
        r"^\s*-\s+\[[ xX]\]\s+(.+?)\s*$",
        body,
        re.MULTILINE,
    ):
        yield match.group(1).strip()
