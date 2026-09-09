"""Lightweight Solidity helpers (no native solc/slither required on Vercel)."""

from __future__ import annotations

import re

from app.core.exceptions import InvalidContractError


PRAGMA_RE = re.compile(r"pragma\s+solidity\s+([^;]+);", re.I)
CONTRACT_RE = re.compile(r"\b(contract|interface|library)\s+(\w+)", re.I)


def extract_pragma(source: str) -> str | None:
    m = PRAGMA_RE.search(source or "")
    return m.group(1).strip() if m else None


def list_contracts(source: str) -> list[str]:
    return [m.group(2) for m in CONTRACT_RE.finditer(source or "")]


def validate_solidity_source(source: str) -> dict:
    if not source or not source.strip():
        raise InvalidContractError("Empty Solidity source.")
    if "contract" not in source and "interface" not in source and "library" not in source:
        # Still allow fragments, but warn via metadata
        contracts = []
    else:
        contracts = list_contracts(source)
    pragma = extract_pragma(source)
    return {
        "pragma": pragma,
        "contracts": contracts,
        "bytes": len(source.encode("utf-8")),
        "lines": source.count("\n") + 1,
    }
