"""Structured findings and reports produced by Control Plane checks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class Severity(IntEnum):
    """Finding severity ordered by operational impact."""

    INFO = 10
    WARNING = 20
    FAIL = 30


@dataclass(frozen=True)
class Finding:
    """One actionable consistency finding."""

    check_id: str
    severity: Severity
    document: str
    message: str
    subject: str | None = None
    evidence: str | None = None
    remediation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "severity": self.severity.name,
            "document": self.document,
            "subject": self.subject,
            "message": self.message,
            "evidence": self.evidence,
            "remediation": self.remediation,
        }


@dataclass(frozen=True)
class ConsistencyReport:
    """Complete result of CP-C01 through CP-C10."""

    findings: tuple[Finding, ...] = ()

    @property
    def status(self) -> str:
        if any(item.severity is Severity.FAIL for item in self.findings):
            return "FAIL"
        if any(item.severity is Severity.WARNING for item in self.findings):
            return "WARNING"
        return "PASS"

    def findings_for(self, check_id: str) -> tuple[Finding, ...]:
        return tuple(
            item for item in self.findings if item.check_id == check_id
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checks": [f"CP-C{number:02d}" for number in range(1, 11)],
            "findings": [item.to_dict() for item in self.findings],
        }
