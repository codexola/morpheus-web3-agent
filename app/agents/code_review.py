"""Code security review agent."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import InvalidRequestError
from app.llm.client import get_llm
from app.llm.prompts import CODE_REVIEW_SYSTEM
from app.models.response import Finding, SecurityReport
from app.models.task import InternalTask
from app.security.patterns import analyze_general_code, analyze_solidity
from app.security.severity import sort_findings


def detect_language(source: str, hint: str | None = None) -> str:
    if hint:
        return hint.lower()
    s = source.lower()
    if "pragma solidity" in s or "contract " in s:
        return "solidity"
    if "def " in s or "import " in s and "from " in s:
        return "python"
    if "function " in s and ("=>" in source or "const " in s or "let " in s):
        return "javascript"
    if "interface " in s and "public " in s and "{" in s:
        return "java"
    return "unknown"


class CodeSecurityAgent:
    capability = "code_security_review"

    async def run(self, task: InternalTask) -> dict[str, Any]:
        source = (
            task.input.get("source_code")
            or task.input.get("source")
            or task.input.get("code")
            or ""
        )
        if not source.strip():
            source = task.description
        if not source.strip():
            raise InvalidRequestError("Provide source_code for code_security_review.")

        filename = task.input.get("filename") or "source"
        language = detect_language(source, task.input.get("language"))
        if language == "solidity":
            findings = analyze_solidity(source, filename=filename)
            findings.extend(analyze_general_code(source, filename=filename))
        else:
            findings = analyze_general_code(source, filename=filename)

        llm = get_llm()
        if llm.available:
            try:
                enriched = await llm.complete_json(
                    system_extra=CODE_REVIEW_SYSTEM,
                    user_content=(
                        f"Language: {language}\n"
                        f"Static findings: {[f.model_dump() for f in findings]}\n"
                        f"Source (untrusted):\n```\n{source[:12000]}\n```"
                    ),
                )
                llm_findings = []
                for i, item in enumerate(enriched.get("findings") or []):
                    try:
                        llm_findings.append(Finding(**{**item, "id": item.get("id") or f"LLM-{i+1:03d}"}))
                    except Exception:
                        continue
                if llm_findings:
                    findings = llm_findings
            except Exception:
                pass

        findings = sort_findings(findings)
        report = SecurityReport.from_findings(
            findings,
            language=language,
            analyzer="pattern+optional-llm",
        )
        return {
            "capability": self.capability,
            "language": language,
            "report": report.model_dump(),
        }
