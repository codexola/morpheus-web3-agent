"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.models.response import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    status = "healthy" if settings.service_state in {"RUNNING", "DEGRADED"} else "unhealthy"
    return HealthResponse(
        status=status,
        version=settings.agent_version,
        state=settings.service_state,
    )
