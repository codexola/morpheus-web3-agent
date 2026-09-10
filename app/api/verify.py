"""Morpheus verification endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.db.connection import db_enabled, ping
from app.models.response import VerifyResponse

router = APIRouter(tags=["morpheus"])


@router.get("/morpheus/verify")
@router.get("/morpheus/verify/")
async def morpheus_verify() -> dict:
    settings = get_settings()
    online = settings.is_online
    accepting = settings.accepts_tasks
    database = "disabled"
    if db_enabled():
        try:
            database = "ok" if await ping() else "error"
        except Exception:
            database = "error"
        if database != "ok":
            online = False
            accepting = False

    status = "ok" if online else "degraded"
    return {
        "status": status,
        "agent": {
            "name": settings.agent_name,
            "version": settings.agent_version,
            "online": online,
            "accepting_tasks": accepting,
            "state": settings.service_state,
            "description": settings.agent_description,
            "database": database,
        },
        "capabilities": list(settings.mvp_capabilities),
    }
