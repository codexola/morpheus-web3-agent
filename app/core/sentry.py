"""Sentry SDK initialization for FastAPI (must run before app creation)."""

from __future__ import annotations

import os

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
_initialized = False


def init_sentry() -> bool:
    """Initialize Sentry as early as possible in the process lifecycle."""
    global _initialized
    if _initialized:
        return True

    dsn = (os.getenv("SENTRY_DSN") or get_settings().sentry_dsn or "").strip()
    if not dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        settings = get_settings()
        release = f"web3dev-ai@{settings.agent_version}"
        if settings.commit and settings.commit != "local":
            release = f"{release}+{settings.commit[:12]}"

        sentry_sdk.init(
            dsn=dsn,
            environment=settings.environment or os.getenv("VERCEL_ENV") or "development",
            release=release,
            send_default_pii=False,
            traces_sample_rate=1.0 if settings.environment != "production" else 0.2,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(level=None, event_level=None),
            ],
        )
        _initialized = True
        logger.info("sentry_initialized", extra={"status": "ok"})
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("sentry_init_failed", extra={"error_class": type(exc).__name__})
        return False
