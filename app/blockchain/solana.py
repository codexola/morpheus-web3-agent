"""Solana JSON-RPC helpers with retries."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.exceptions import InvalidAddressError, RpcUnavailableError
from app.core.security import looks_like_solana_address

_RETRYABLE = {429, 502, 503, 504}


async def solana_rpc(method: str, params: list[Any]) -> Any:
    settings = get_settings()
    if not settings.solana_rpc_url:
        raise RpcUnavailableError("Solana RPC URL not configured.")
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=settings.rpc_timeout_seconds) as client:
                resp = await client.post(settings.solana_rpc_url, json=payload)
                if resp.status_code in _RETRYABLE:
                    last_error = RpcUnavailableError(f"Solana RPC HTTP {resp.status_code}")
                    await asyncio.sleep(2**attempt)
                    continue
                resp.raise_for_status()
                data = resp.json()
            if "error" in data:
                raise RpcUnavailableError(str(data["error"]))
            return data.get("result")
        except RpcUnavailableError:
            raise
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(2**attempt)
    raise RpcUnavailableError(f"Solana RPC failed: {last_error}") from last_error


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
