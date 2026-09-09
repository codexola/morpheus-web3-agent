"""Morpheus verification endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.models.response import VerifyResponse

router = APIRouter(tags=["morpheus"])


@router.get("/morpheus/verify", response_model=VerifyResponse)
async def morpheus_verify() -> VerifyResponse:
    settings = get_settings()
    online = settings.service_state in {"RUNNING", "DEGRADED"}
    return VerifyResponse(
        status="ok",
        agent={
            "name": settings.agent_name,
            "version": settings.agent_version,
            "online": online,
            "state": settings.service_state,
            "description": settings.agent_description,
        },
        capabilities=list(settings.mvp_capabilities),
    )
