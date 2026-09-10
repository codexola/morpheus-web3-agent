"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.db.connection import db_enabled, ping
from app.models.response import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    online = settings.is_online
    db_ok: bool | None = None
    if db_enabled():
        try:
            db_ok = await ping()
        except Exception:
            db_ok = False
        if db_ok is False:
            online = False

    status = "healthy" if online else "unhealthy"
    body = HealthResponse(
        status=status,
        version=settings.agent_version,
        state=settings.service_state,
    ).model_dump()
    body["database"] = "ok" if db_ok else ("error" if db_ok is False else "disabled")
    return body
