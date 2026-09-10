"""Task API routes."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request

from app.core.config import get_settings
from app.core.exceptions import AgentError
from app.core.logging import get_logger
from app.core.rate_limit import check_rate_limit
from app.core.security import client_ip, require_optional_shared_secret
from app.models.task import TaskSubmitRequest
from app.services import tasks as task_service
from app.services.results import public_result

router = APIRouter(prefix="/api", tags=["tasks"])
logger = get_logger(__name__)


async def _enforce_size_and_rate(request: Request) -> None:
    settings = get_settings()
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit():
        if int(content_length) > settings.max_json_bytes:
            from app.core.exceptions import InvalidRequestError

            raise InvalidRequestError("Payload exceeds size limit.")
    await check_rate_limit(client_ip(request), settings.rate_limit_per_minute)


@router.post("/tasks")
async def create_task(
    request: Request,
    body: TaskSubmitRequest,
    _: None = Depends(require_optional_shared_secret),
) -> dict:
    await _enforce_size_and_rate(request)
    started = time.time()
    task = await task_service.submit_and_process(body)
    duration_ms = int((time.time() - started) * 1000)
    logger.info(
        "task_completed",
        extra={
            "capability": task.capability,
            "duration_ms": duration_ms,
            "status": task.status.value,
        },
    )
    return public_result(task)


@router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> dict:
    task = await task_service.store.get(task_id)
    if not task:
        task = await task_service.store.get_by_external(task_id)
    if not task:
        raise AgentError("INVALID_REQUEST", "Task not found.", status_code=404)
    return public_result(task)


@router.get("/v1/tasks/{task_id}")
async def get_task_v1(task_id: str) -> dict:
    return await get_task(task_id)


@router.post("/v1/tasks")
async def create_task_v1(
    request: Request,
    body: TaskSubmitRequest,
    _: None = Depends(require_optional_shared_secret),
) -> dict:
    return await create_task(request, body, _)
