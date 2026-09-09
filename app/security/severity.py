"""Severity helpers."""

from __future__ import annotations

ORDER = ["critical", "high", "medium", "low", "informational"]


def severity_rank(value: str) -> int:
    try:
        return ORDER.index(value)
    except ValueError:
        return len(ORDER)


def sort_findings(findings: list) -> list:
    return sorted(findings, key=lambda f: (severity_rank(f.severity), -f.confidence))
