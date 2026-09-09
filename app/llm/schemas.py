"""LLM JSON schemas (documentation helpers)."""

FINDING_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "severity": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low", "informational"],
        },
        "confidence": {"type": "number"},
        "location": {"type": "string"},
        "description": {"type": "string"},
        "impact": {"type": "string"},
        "recommendation": {"type": "string"},
    },
    "required": ["id", "title", "severity", "description"],
}
