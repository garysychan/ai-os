"""Control Plane version metadata validation."""

from __future__ import annotations

import re
from collections.abc import Mapping

from .findings import Finding, Severity

_SEMVER_RE = re.compile(r"^(?:0|[1-9]\\d*)\\.(?:0|[1-9]\\d*)\\.(?:0|[1-9]\\d*)$")
_CONTROL_VERSION_RE = re.compile(
    r"^\\s*(?:>\\s*)?Control Plane Version:\\s*([0-9]+\\.[0-9]+\\.[0-9]+)\\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_VERSION_RE = re.compile(
    r"^\\s*(?:>\\s*)?Version:\\s*([0-9]+\\.[0-9]+\\.[0-9]+)\\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def check_versions(documents: Mapping[str, str]) -> list[Finding]:
    """Return CP-C09 findings without treating legacy metadata as fatal."""
    findings: list[Finding] = []
    control = documents.get("CONTROL_PLANE.md", "")
    match = _CONTROL_VERSION_RE.search(control) or _VERSION_RE.search(control)
    control_version = match.group(1) if match else None

    if not control_version:
        findings.append(
            Finding(
                check_id="CP-C09",
                severity=Severity.WARNING,
                document="CONTROL_PLANE.md",
                message="Control Plane version metadata is missing",
                remediation="Declare Control Plane Version using semantic versioning",
            )
        )
        return findings

    if not _SEMVER_RE.fullmatch(control_version):
        findings.append(
            Finding(
                check_id="CP-C09",
                severity=Severity.FAIL,
                document="CONTROL_PLANE.md",
                message="Control Plane version is not valid semantic versioning",
                evidence=control_version,
                remediation="Use MAJOR.MINOR.PATCH",
            )
        )

    for name, markdown in documents.items():
        if name == "CONTROL_PLANE.md":
            continue
        document_match = _CONTROL_VERSION_RE.search(markdown)
        if not document_match:
            findings.append(
                Finding(
                    check_id="CP-C09",
                    severity=Severity.WARNING,
                    document=name,
                    message="Controlled document does not declare Control Plane Version",
                    remediation=(
                        f"Declare Control Plane Version: {control_version} "
                        "through approved Change Control"
                    ),
                )
            )
        elif document_match.group(1).split(".", 1)[0] != control_version.split(".", 1)[0]:
            findings.append(
                Finding(
                    check_id="CP-C09",
                    severity=Severity.FAIL,
                    document=name,
                    message="Incompatible Control Plane major version",
                    evidence=document_match.group(1),
                    remediation=f"Align with Control Plane {control_version}",
                )
            )
    return findings
