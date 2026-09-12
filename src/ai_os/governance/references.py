"""Cross-document Markdown reference validation."""

from __future__ import annotations

import re
from collections.abc import Mapping

from .findings import Finding, Severity

_MARKDOWN_REFERENCE_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])([A-Z][A-Z0-9_/-]*\\.md)\\b"
)


def check_document_references(
    documents: Mapping[str, str],
) -> list[Finding]:
    """Return CP-C02 findings for referenced Markdown documents."""
    findings: list[Finding] = []
    known = set(documents)

    for source, markdown in documents.items():
        for reference in sorted(set(_MARKDOWN_REFERENCE_RE.findall(markdown))):
            basename = reference.rsplit("/", 1)[-1]
            if basename in known:
                continue
            findings.append(
                Finding(
                    check_id="CP-C02",
                    severity=Severity.FAIL,
                    document=source,
                    subject=reference,
                    message="Referenced Control Plane document does not exist",
                    evidence=reference,
                    remediation="Add the document or correct the reference",
                )
            )
    return findings
