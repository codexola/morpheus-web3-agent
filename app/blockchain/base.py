"""Base chain helpers (reuse EVM client)."""

from app.blockchain.ethereum import get_code, get_native_balance, get_transaction

__all__ = ["get_code", "get_native_balance", "get_transaction"]
