"""Response / report schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low", "informational"]


class Finding(BaseModel):
    id: str
    title: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    location: str | None = None
    description: str
    impact: str = ""
    recommendation: str = ""
    category: str | None = None


class SecuritySummary(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    informational: int = 0


class SecurityReport(BaseModel):
    summary: SecuritySummary
    findings: list[Finding] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_findings(
        cls,
        findings: list[Finding],
        **metadata: Any,
    ) -> SecurityReport:
        summary = SecuritySummary()
        for f in findings:
            setattr(summary, f.severity, getattr(summary, f.severity) + 1)
        return cls(summary=summary, findings=findings, metadata=metadata)


class HealthResponse(BaseModel):
    status: str
    version: str
    state: str | None = None


class VerifyResponse(BaseModel):
    status: str
    agent: dict[str, Any]
    capabilities: list[str]


class CapabilityInfo(BaseModel):
    id: str
    name: str
    description: str


class RootResponse(BaseModel):
    service: str
    version: str
    status: str
    docs: str = "/docs"
