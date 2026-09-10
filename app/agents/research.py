"""Web3 research agent."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.core.config import get_settings
from app.core.exceptions import InvalidRequestError
from app.core.security import assert_safe_url
from app.llm.client import get_llm
from app.llm.prompts import RESEARCH_SYSTEM
from app.models.task import InternalTask


async def _safe_fetch(url: str) -> tuple[str, list[dict[str, str]]]:
    """Fetch URL without following unsafe redirects."""
    settings = get_settings()
    sources: list[dict[str, str]] = []
    current = assert_safe_url(url)
    live_excerpt = ""

    async with httpx.AsyncClient(
        timeout=settings.http_timeout_seconds,
        follow_redirects=False,
        headers={"User-Agent": "Web3DevAI/1.0 (+research)"},
    ) as client:
        for _ in range(5):
            resp = await client.get(current)
            if resp.status_code in {301, 302, 303, 307, 308}:
                location = resp.headers.get("location")
                if not location:
                    sources.append({"url": current, "status": "redirect_missing_location"})
                    break
                next_url = urljoin(current, location)
                # Re-validate every hop (blocks redirect-to-metadata SSRF)
                current = assert_safe_url(next_url)
                continue
            if resp.status_code >= 400:
                sources.append({"url": current, "status": f"http_{resp.status_code}"})
                break
            live_excerpt = resp.text[:8000]
            sources.append({"url": current, "status": "fetched"})
            break
        else:
            sources.append({"url": current, "status": "redirect_limit"})

    return live_excerpt, sources


class ResearchAgent:
    capability = "web3_research"

    async def run(self, task: InternalTask) -> dict[str, Any]:
        query = (
            task.input.get("query")
            or task.input.get("topic")
            or task.description
            or ""
        ).strip()
        if not query:
            raise InvalidRequestError("Provide a research query/description.")

        sources: list[dict[str, str]] = []
        live_excerpt = ""
        url = task.input.get("url")
        if url:
            try:
                live_excerpt, sources = await _safe_fetch(url)
            except Exception as exc:
                sources.append(
                    {
                        "url": str(urlparse(str(url)).geturl()),
                        "status": f"error:{type(exc).__name__}",
                    }
                )

        llm = get_llm()
        if llm.available:
            try:
                report = await llm.complete_json(
                    system_extra=RESEARCH_SYSTEM,
                    user_content=(
                        f"Research topic: {query}\n"
                        f"Optional live excerpt:\n{live_excerpt[:6000]}\n"
                        "Return the research JSON schema."
                    ),
                )
                report.setdefault("sources", sources)
                report["capability"] = self.capability
                report["mode"] = "llm+optional-live"
                return report
            except Exception:
                pass

        return {
            "capability": self.capability,
            "mode": "heuristic-fallback",
            "executive_summary": (
                f"Structured research outline for '{query}'. "
                "Configure OPENAI_API_KEY for deeper synthesis; live URL fetch used when provided."
            ),
            "protocol_overview": f"Subject: {query}",
            "technology": "Not fully determined without live documentation / LLM enrichment.",
            "token_model": "Unknown / not provided in input.",
            "governance": "Unknown / not provided in input.",
            "competition": [],
            "security_history": [],
            "risks": [
                "Information may be incomplete without verified primary sources.",
                "Market and TVL figures change rapidly and should be re-checked on-chain/off-chain.",
            ],
            "opportunities": [
                "Further analysis can incorporate docs URL, contract addresses, and governance forums.",
            ],
            "sources": sources,
            "confidence": 0.35 if not live_excerpt else 0.5,
            "query": query,
        }
