"""Solana JSON-RPC helpers."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import InvalidAddressError, RpcUnavailableError
from app.core.security import looks_like_solana_address


async def solana_rpc(method: str, params: list[Any]) -> Any:
    settings = get_settings()
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        async with httpx.AsyncClient(timeout=settings.rpc_timeout_seconds) as client:
            resp = await client.post(settings.solana_rpc_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        raise RpcUnavailableError(f"Solana RPC failed: {exc}") from exc
    if "error" in data:
        raise RpcUnavailableError(str(data["error"]))
    return data.get("result")


async def get_balance(address: str) -> dict[str, Any]:
    if not looks_like_solana_address(address):
        raise InvalidAddressError("Invalid Solana address.")
    result = await solana_rpc("getBalance", [address])
    lamports = (result or {}).get("value", 0)
    return {
        "chain": "solana",
        "address": address,
        "balance_lamports": lamports,
        "balance_sol": lamports / 1_000_000_000,
    }


async def get_signatures(address: str, limit: int = 10) -> dict[str, Any]:
    if not looks_like_solana_address(address):
        raise InvalidAddressError("Invalid Solana address.")
    result = await solana_rpc(
        "getSignaturesForAddress",
        [address, {"limit": min(limit, 25)}],
    )
    return {"chain": "solana", "address": address, "signatures": result or []}
