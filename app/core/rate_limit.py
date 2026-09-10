"""Optional Redis / Upstash rate limiting with in-memory fallback."""

from __future__ import annotations

import time

import httpx

from app.core.config import get_settings
from app.core.exceptions import RateLimitedError
from app.core.logging import get_logger

logger = get_logger(__name__)


class MemoryRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}

    def check(self, key: str, limit: int, window_seconds: float = 60.0) -> None:
        now = time.time()
        bucket = self._hits.setdefault(key, [])
        self._hits[key] = [t for t in bucket if now - t < window_seconds]
        if len(self._hits[key]) >= limit:
            raise RateLimitedError(f"Rate limit exceeded ({limit}/min).")
        self._hits[key].append(now)


class RedisRateLimiter:
    """Upstash REST Redis rate limiter (works on Vercel serverless)."""

    def __init__(self, rest_url: str, rest_token: str) -> None:
        self.rest_url = rest_url.rstrip("/")
        self.rest_token = rest_token

    async def check(self, key: str, limit: int, window_seconds: float = 60.0) -> None:
        redis_key = f"rl:{key}"
        headers = {"Authorization": f"Bearer {self.rest_token}"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            incr = await client.post(
                f"{self.rest_url}/incr/{redis_key}",
                headers=headers,
            )
            incr.raise_for_status()
            count = int(incr.json().get("result", 0))
            if count == 1:
                await client.post(
                    f"{self.rest_url}/expire/{redis_key}/{int(window_seconds)}",
                    headers=headers,
                )
            if count > limit:
                raise RateLimitedError(f"Rate limit exceeded ({limit}/min).")


_memory = MemoryRateLimiter()
_redis: RedisRateLimiter | None = None


def _redis_from_env() -> RedisRateLimiter | None:
    settings = get_settings()
    # Upstash KV via Vercel typically injects KV_REST_API_URL + KV_REST_API_TOKEN
    # or UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN / REDIS_URL
    import os

    url = (
        os.getenv("KV_REST_API_URL")
        or os.getenv("UPSTASH_REDIS_REST_URL")
        or ""
    ).strip()
    token = (
        os.getenv("KV_REST_API_TOKEN")
        or os.getenv("UPSTASH_REDIS_REST_TOKEN")
        or ""
    ).strip()
    if url and token:
        return RedisRateLimiter(url, token)
    # REDIS_URL alone is TCP; skip on serverless without REST credentials
    _ = settings.redis_url
    return None


async def check_rate_limit(key: str, limit: int, window_seconds: float = 60.0) -> None:
    global _redis
    if _redis is None:
        _redis = _redis_from_env()
    if _redis is not None:
        try:
            await _redis.check(key, limit, window_seconds)
            return
        except RateLimitedError:
            raise
        except Exception as exc:
            logger.warning("redis_rate_limit_fallback", extra={"error_class": type(exc).__name__})
    _memory.check(key, limit, window_seconds)
