"""Morpheus callback receiver."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, Request

from app.core.config import get_settings
from app.core.exceptions import InvalidRequestError
from app.core.logging import get_logger, redact

router = APIRouter(tags=["callbacks"])
logger = get_logger(__name__)


@router.post("/callbacks/morpheus")
async def morpheus_callback(
    request: Request,
    x_callback_secret: str | None = Header(default=None, alias="X-Callback-Secret"),
) -> dict[str, Any]:
    settings = get_settings()
    expected = settings.callback_shared_secret or settings.morpheus_shared_secret
    if expected and x_callback_secret != expected:
        raise InvalidRequestError("Invalid callback secret.")

    payload = await request.json()
    logger.info("morpheus_callback_received", extra={"status": "ok"})
    logger.debug("callback_payload=%s", redact(payload))
    return {"success": True, "received": True}
