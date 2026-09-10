"""Optional Sentry initialization."""

from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
_initialized = False


def init_sentry() -> bool:
    global _initialized
    if _initialized:
        return True
    settings = get_settings()
    if not settings.sentry_dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1,
            integrations=[FastApiIntegration()],
        )
        _initialized = True
        logger.info("sentry_initialized", extra={"status": "ok"})
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("sentry_init_failed", extra={"error_class": type(exc).__name__})
        return False
