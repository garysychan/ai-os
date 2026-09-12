"""Control Plane permission-table validation."""

from __future__ import annotations

import re
from collections.abc import Mapping

from .findings import Finding, Severity

_TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")
_TRUE_VALUES = {"yes", "true", "allowed", "allow"}


def _rows(markdown: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in markdown.splitlines():
        match = _TABLE_ROW_RE.match(line.strip())
        if not match:
            continue
        cells = [
            re.sub(r"[\x60*]", "", cell).strip()
            for cell in match.group(1).split("|")
        ]
        if cells and not all(set(cell) <= {"-", ":"} for cell in cells):
            rows.append(cells)
    return rows


def check_permissions(documents: Mapping[str, str]) -> list[Finding]:
    """Return CP-C03/CP-C08 findings for unauthorized modification rights."""
    findings: list[Finding] = []

    agents_rows = _rows(documents.get("AGENTS.md", ""))
    if agents_rows:
        header = next(
            (
                row for row in agents_rows
                if "Modify Control Files" in row
            ),
            None,
        )
        if header:
            column = header.index("Modify Control Files")
            for row in agents_rows:
                if row is header or len(row) <= column:
                    continue
                actor = row[0].strip()
                permission = row[column].strip().casefold()
                if actor.casefold() != "human" and permission in _TRUE_VALUES:
                    findings.append(
                        Finding(
                            check_id="CP-C08",
                            severity=Severity.FAIL,
                            document="AGENTS.md",
                            subject=actor,
                            message="Agent has unauthorized Control Plane modification rights",
                            evidence=row[column],
                            remediation="Set Modify Control Files to No",
                        )
                    )

    control_rows = _rows(documents.get("CONTROL_PLANE.md", ""))
    header = next(
        (row for row in control_rows if "Direct Modify" in row),
        None,
    )
    if header:
        column = header.index("Direct Modify")
        for row in control_rows:
            if row is header or len(row) <= column:
                continue
            actor = row[0].strip()
            permission = row[column].strip().casefold()
            if actor.casefold() != "human" and permission in _TRUE_VALUES:
                findings.append(
                    Finding(
                        check_id="CP-C08",
                        severity=Severity.FAIL,
                        document="CONTROL_PLANE.md",
                        subject=actor,
                        message="Non-human actor has direct modification rights",
                        evidence=row[column],
                        remediation="Require Change Control and human approval",
                    )
                )
    return findings
