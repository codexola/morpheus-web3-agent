"""Deterministic task router."""

from __future__ import annotations

from typing import Any, Protocol

from app.agents.blockchain import BlockchainAnalyticsAgent
from app.agents.code_review import CodeSecurityAgent
from app.agents.research import ResearchAgent
from app.agents.smart_contract import SmartContractAgent
from app.core.exceptions import UnsupportedCapabilityError
from app.models.task import InternalTask


class Agent(Protocol):
    capability: str

    async def run(self, task: InternalTask) -> dict[str, Any]: ...


_AGENTS: dict[str, Agent] = {
    "smart_contract_audit": SmartContractAgent(),
    "code_security_review": CodeSecurityAgent(),
    "blockchain_analytics": BlockchainAnalyticsAgent(),
    "web3_research": ResearchAgent(),
}


def get_agent(capability: str) -> Agent:
    agent = _AGENTS.get(capability)
    if not agent:
        raise UnsupportedCapabilityError(capability)
    return agent


async def route_and_run(task: InternalTask) -> dict[str, Any]:
    agent = get_agent(task.capability)
    return await agent.run(task)
