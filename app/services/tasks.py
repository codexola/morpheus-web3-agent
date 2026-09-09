"""In-memory task store with idempotency (optional Postgres later via DATABASE_URL)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError
from app.core.logging import get_logger, task_id_ctx
from app.models.task import InternalTask, TaskStatus, TaskSubmitRequest, adapt_morpheus_request
from app.agents.router import route_and_run
from app.core.exceptions import AgentError, error_body

logger = get_logger(__name__)


class TaskStore:
    def __init__(self) -> None:
        self._by_id: dict[str, InternalTask] = {}
        self._by_external: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def get(self, task_id: str) -> InternalTask | None:
        return self._by_id.get(task_id)

    async def get_by_external(self, external_task_id: str) -> InternalTask | None:
        tid = self._by_external.get(external_task_id)
        return self._by_id.get(tid) if tid else None

    async def save(self, task: InternalTask) -> InternalTask:
        async with self._lock:
            self._by_id[task.task_id] = task
            self._by_external[task.external_task_id] = task.task_id
            return task

    def active_count(self) -> int:
        return sum(
            1
            for t in self._by_id.values()
            if t.status in {TaskStatus.ACCEPTED, TaskStatus.PROCESSING}
        )


store = TaskStore()


async def submit_task(raw: TaskSubmitRequest) -> InternalTask:
    settings = get_settings()
    if not settings.accepts_tasks:
        raise ServiceUnavailableError(
            f"Service state is {settings.service_state}; not accepting tasks."
        )

    # Idempotency: same external id returns existing task
    external = raw.external_task_id or raw.task_id or raw.id
    if external:
        existing = await store.get_by_external(external)
        if existing:
            return existing

    if store.active_count() >= settings.max_active_tasks:
        raise ServiceUnavailableError("Too many active tasks.")

    task = adapt_morpheus_request(raw)
    await store.save(task)
    return task


async def process_task(task_id: str) -> InternalTask:
    task = await store.get(task_id)
    if not task:
        raise AgentError("INVALID_REQUEST", "Task not found.", status_code=404)
    if task.status in {TaskStatus.SUCCESS, TaskStatus.FAILED}:
        return task

    task.status = TaskStatus.PROCESSING
    task.started_at = datetime.now(timezone.utc)
    await store.save(task)
    task_id_ctx.set(task.task_id)

    try:
        result = await route_and_run(task)
        task.result = result
        task.status = TaskStatus.SUCCESS
        task.error = None
    except AgentError as exc:
        task.status = TaskStatus.FAILED
        task.error = error_body(exc)["error"]
        logger.error("task_failed", extra={"error_class": exc.code, "status": "failed"})
    except Exception as exc:  # pragma: no cover
        task.status = TaskStatus.FAILED
        task.error = {
            "code": "INTERNAL_ERROR",
            "message": str(exc),
            "retryable": True,
        }
        logger.error("task_failed", extra={"error_class": type(exc).__name__, "status": "failed"})

    task.completed_at = datetime.now(timezone.utc)
    await store.save(task)
    return task


async def submit_and_process(raw: TaskSubmitRequest) -> InternalTask:
    task = await submit_task(raw)
    if task.status in {TaskStatus.SUCCESS, TaskStatus.FAILED}:
        return task
    # For serverless reliability, process inline within the request.
    return await process_task(task.task_id)
