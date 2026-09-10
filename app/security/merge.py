"""Finding merge helpers."""

from __future__ import annotations

from app.models.response import Finding


def merge_findings(static: list[Finding], llm: list[Finding]) -> list[Finding]:
    """Keep all static findings; enrich matching LLM rows; append LLM-only extras."""
    by_key: dict[str, Finding] = {}
    for f in static:
        key = f"{f.title}|{f.location or ''}"
        by_key[key] = f
    for f in llm:
        key = f"{f.title}|{f.location or ''}"
        if key in by_key:
            base = by_key[key]
            by_key[key] = base.model_copy(
                update={
                    "description": f.description or base.description,
                    "impact": f.impact or base.impact,
                    "recommendation": f.recommendation or base.recommendation,
                    "confidence": max(base.confidence, f.confidence),
                }
            )
        else:
            by_key[key] = f
    return list(by_key.values())
