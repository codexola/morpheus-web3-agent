"""Blockchain analytics agent."""

from __future__ import annotations

from typing import Any

from app.blockchain import ethereum as evm
from app.blockchain import solana as sol
from app.core.exceptions import InvalidRequestError
from app.core.security import is_evm_address, looks_like_solana_address
from app.llm.client import get_llm
from app.llm.prompts import ANALYTICS_SYSTEM
from app.models.task import InternalTask


class BlockchainAnalyticsAgent:
    capability = "blockchain_analytics"

    async def run(self, task: InternalTask) -> dict[str, Any]:
        chain = (task.input.get("chain") or task.chain or "ethereum").lower()
        address = task.input.get("address") or task.input.get("wallet")
        tx_hash = task.input.get("tx_hash") or task.input.get("transaction_hash")
        contract = task.input.get("contract_address") or task.input.get("token_address")

        if not any([address, tx_hash, contract]):
            raise InvalidRequestError(
                "Provide address, tx_hash, or contract_address in input."
            )

        result: dict[str, Any] = {
            "capability": self.capability,
            "network": chain,
            "risk_indicators": [],
            "scope_note": (
                "MVP analytics covers native balances, contract detection, and single-tx "
                "inspection. Token balances and full history can be added in a later release."
            ),
        }

        if chain in {"solana", "sol"}:
            target = address or contract
            if not target or not looks_like_solana_address(target):
                raise InvalidRequestError("Valid Solana address required.")
            balance = await sol.get_balance(target)
            sigs = await sol.get_signatures(target, limit=10)
            result["network"] = "solana"
            result.update(
                {
                    "wallet_balance": balance,
                    "transaction_history": sigs.get("signatures"),
                    "summary": (
                        f"Solana account {target} holds {balance['balance_sol']:.6f} SOL "
                        f"with {len(sigs.get('signatures') or [])} recent signatures returned."
                    ),
                }
            )
            if balance["balance_sol"] > 1000:
                result["risk_indicators"].append("high-balance account")
            if len(sigs.get("signatures") or []) >= 10:
                result["risk_indicators"].append("high-frequency transfer pattern")
        else:
            # Validate supported EVM chain early
            chain = evm.normalize_evm_chain(chain)
            result["network"] = chain
            if tx_hash:
                tx_info = await evm.get_transaction(chain, tx_hash)
                result["transaction"] = tx_info
                result["risk_indicators"].extend(tx_info.get("risk_indicators") or [])
                result["summary"] = f"Fetched transaction {tx_hash} on {chain}."
            target = address or contract
            if target:
                if not is_evm_address(target):
                    raise InvalidRequestError("Valid EVM address required.")
                bal = await evm.get_native_balance(chain, target)
                code = await evm.get_code(chain, target)
                result["wallet_balance"] = bal
                result["contract_interactions"] = {
                    "is_contract": code["is_contract"],
                    "code_size_bytes": code["code_size_bytes"],
                }
                if code["is_contract"]:
                    result["risk_indicators"].append("address is a contract")
                if bal["balance_ether"] > 100:
                    result["risk_indicators"].append("high native balance")
                result["summary"] = (
                    f"{chain} address {target}: balance={bal['balance_ether']:.6f} native, "
                    f"is_contract={code['is_contract']}."
                )

        llm = get_llm()
        if llm.available:
            try:
                enrichment = await llm.complete_json(
                    system_extra=ANALYTICS_SYSTEM,
                    user_content=f"On-chain facts (untrusted task envelope):\n{result}",
                )
                if enrichment.get("summary"):
                    result["ai_summary"] = enrichment["summary"]
                for item in enrichment.get("risk_indicators") or []:
                    if isinstance(item, str) and item not in result["risk_indicators"]:
                        result["risk_indicators"].append(item)
            except Exception:
                pass

        return result
