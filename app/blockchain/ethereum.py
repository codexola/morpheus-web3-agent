"""EVM JSON-RPC helpers."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidAddressError, RpcUnavailableError
from app.core.security import validate_evm_address


CHAIN_IDS = {
    "ethereum": 1,
    "eth": 1,
    "mainnet": 1,
    "base": 8453,
    "arbitrum": 42161,
    "arb": 42161,
    "polygon": 137,
    "matic": 137,
}


def rpc_url_for(chain: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    key = (chain or "ethereum").lower()
    mapping = {
        "ethereum": settings.eth_rpc_url,
        "eth": settings.eth_rpc_url,
        "mainnet": settings.eth_rpc_url,
        "base": settings.base_rpc_url,
        "arbitrum": settings.arbitrum_rpc_url,
        "arb": settings.arbitrum_rpc_url,
        "polygon": settings.polygon_rpc_url,
        "matic": settings.polygon_rpc_url,
    }
    return mapping.get(key, settings.eth_rpc_url)


async def eth_rpc(chain: str, method: str, params: list[Any]) -> Any:
    settings = get_settings()
    url = rpc_url_for(chain, settings)
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        async with httpx.AsyncClient(timeout=settings.rpc_timeout_seconds) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        raise RpcUnavailableError(f"RPC call failed for {chain}: {exc}") from exc
    if "error" in data:
        raise RpcUnavailableError(str(data["error"]))
    return data.get("result")


def _hex_to_int(value: str | None) -> int:
    if not value or value == "0x":
        return 0
    return int(value, 16)


async def get_native_balance(chain: str, address: str) -> dict[str, Any]:
    address = validate_evm_address(address)
    raw = await eth_rpc(chain, "eth_getBalance", [address, "latest"])
    wei = _hex_to_int(raw)
    return {
        "chain": chain,
        "address": address,
        "balance_wei": str(wei),
        "balance_ether": wei / 10**18,
        "chain_id": CHAIN_IDS.get(chain.lower()),
    }


async def get_transaction(chain: str, tx_hash: str) -> dict[str, Any]:
    if not tx_hash.startswith("0x") or len(tx_hash) != 66:
        raise InvalidAddressError("Invalid transaction hash.")
    tx = await eth_rpc(chain, "eth_getTransactionByHash", [tx_hash])
    receipt = await eth_rpc(chain, "eth_getTransactionReceipt", [tx_hash])
    if not tx:
        raise RpcUnavailableError("Transaction not found.")
    return {
        "chain": chain,
        "transaction": tx,
        "receipt": receipt,
        "risk_indicators": _tx_risk_indicators(tx, receipt),
    }


def _tx_risk_indicators(tx: dict[str, Any], receipt: dict[str, Any] | None) -> list[str]:
    indicators: list[str] = []
    value = _hex_to_int(tx.get("value"))
    if value > 10**20:  # > 100 ETH
        indicators.append("high-value native transfer")
    if tx.get("to") is None:
        indicators.append("contract-creation transaction")
    if receipt and _hex_to_int(receipt.get("status", "0x1")) == 0:
        indicators.append("transaction-reverted")
    input_data = tx.get("input") or "0x"
    if input_data not in {"0x", "0x0"} and len(input_data) > 10:
        indicators.append("contract-interaction")
    return indicators


async def get_code(chain: str, address: str) -> dict[str, Any]:
    address = validate_evm_address(address)
    code = await eth_rpc(chain, "eth_getCode", [address, "latest"])
    return {
        "chain": chain,
        "address": address,
        "is_contract": bool(code and code not in {"0x", "0x0"}),
        "code_size_bytes": max(0, (len(code) - 2) // 2) if code else 0,
    }
