"""Security helpers: SSRF guards, auth, payload limits."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from fastapi import Header, Request

from app.core.config import get_settings
from app.core.exceptions import InvalidRequestError, RateLimitedError

_BLOCKED_HOSTS = {
    "localhost",
    "metadata.google.internal",
    "metadata",
}

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def assert_safe_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise InvalidRequestError("Only http/https URLs are allowed.")
    host = (parsed.hostname or "").lower()
    if not host or host in _BLOCKED_HOSTS or host.endswith(".local"):
        raise InvalidRequestError("URL host is not allowed.")
    try:
        ip = ipaddress.ip_address(host)
        for net in _PRIVATE_NETWORKS:
            if ip in net:
                raise InvalidRequestError("Private/metadata IP addresses are blocked.")
    except ValueError:
        # hostname is not a literal IP
        pass
    return url


_EVM_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
_TX_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")
_SOLANA_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def validate_evm_address(value: str) -> str:
    if not _EVM_RE.match(value or ""):
        raise InvalidRequestError("Invalid EVM address.")
    return value


def validate_tx_hash(value: str) -> str:
    if not _TX_RE.match(value or ""):
        raise InvalidRequestError("Invalid transaction hash.")
    return value


def looks_like_solana_address(value: str) -> bool:
    return bool(_SOLANA_RE.match(value or ""))


class RateLimiter:
    """Simple in-process sliding window rate limiter."""

    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}

    def check(self, key: str, limit: int, window_seconds: float = 60.0) -> None:
        import time

        now = time.time()
        bucket = self._hits.setdefault(key, [])
        self._hits[key] = [t for t in bucket if now - t < window_seconds]
        if len(self._hits[key]) >= limit:
            raise RateLimitedError(f"Rate limit exceeded ({limit}/min).")
        self._hits[key].append(now)


rate_limiter = RateLimiter()


async def require_optional_shared_secret(
    request: Request,
    x_morpheus_secret: str | None = Header(default=None, alias="X-Morpheus-Secret"),
) -> None:
    settings = get_settings()
    expected = settings.morpheus_shared_secret
    if not expected:
        return
    if x_morpheus_secret != expected:
        raise InvalidRequestError("Invalid shared secret.")


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"
