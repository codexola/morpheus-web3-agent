"""Smart contract audit agent."""

from __future__ import annotations

from typing import Any

from app.core.exceptions import InvalidContractError
from app.llm.client import get_llm
from app.llm.prompts import SMART_CONTRACT_SYSTEM
from app.models.response import Finding, SecurityReport
from app.models.task import InternalTask
from app.security.patterns import analyze_solidity
from app.security.severity import sort_findings
from app.security.solidity import validate_solidity_source


class SmartContractAgent:
    capability = "smart_contract_audit"

    async def run(self, task: InternalTask) -> dict[str, Any]:
        source = (
            task.input.get("source_code")
            or task.input.get("source")
            or task.input.get("code")
            or task.input.get("contract")
            or ""
        )
        if not source and task.description:
            # Allow description-only with embedded code fences
            source = task.description
        if not source.strip():
            raise InvalidContractError("Provide Solidity source_code in input.")

        filename = task.input.get("filename") or "Contract.sol"
        meta = validate_solidity_source(source)
        findings = analyze_solidity(source, filename=filename)

        llm = get_llm()
        if llm.available and findings:
            try:
                enriched = await llm.complete_json(
                    system_extra=SMART_CONTRACT_SYSTEM,
                    user_content=(
                        f"Static findings JSON:\n{[f.model_dump() for f in findings]}\n\n"
                        f"Source (untrusted):\n```solidity\n{source[:12000]}\n```"
                    ),
                    model=None,
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
            analyzer="pattern+optional-llm",
            pragma=meta.get("pragma"),
            contracts=meta.get("contracts"),
            chain=task.input.get("chain") or task.chain,
        )
        return {
            "capability": self.capability,
            "report": report.model_dump(),
            "contract_metadata": meta,
        }
