"""In-memory task store with atomic idempotency."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.agents.router import route_and_run
from app.core.config import get_settings
from app.core.exceptions import AgentError, ServiceUnavailableError, error_body
from app.core.logging import get_logger, task_id_ctx
from app.core.security import assert_safe_url
from app.models.task import InternalTask, TaskStatus, TaskSubmitRequest, adapt_morpheus_request

logger = get_logger(__name__)


class TaskStore:
    def __init__(self) -> None:
        self._by_id: dict[str, InternalTask] = {}
        self._by_external: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def get(self, task_id: str) -> InternalTask | None:
        async with self._lock:
            return self._by_id.get(task_id)

    async def get_by_external(self, external_task_id: str) -> InternalTask | None:
        async with self._lock:
            tid = self._by_external.get(external_task_id)
            return self._by_id.get(tid) if tid else None

    async def save(self, task: InternalTask) -> InternalTask:
        async with self._lock:
            self._by_id[task.task_id] = task
            self._by_external[task.external_task_id] = task.task_id
            return task

    async def create_or_get(self, raw: TaskSubmitRequest) -> tuple[InternalTask, bool]:
        """Atomically create a task or return existing by external id."""
        settings = get_settings()
        async with self._lock:
            external = raw.external_task_id or raw.task_id or raw.id
            if external:
                tid = self._by_external.get(external)
                if tid and tid in self._by_id:
                    return self._by_id[tid], False

            active = sum(
                1
                for t in self._by_id.values()
                if t.status in {TaskStatus.ACCEPTED, TaskStatus.PROCESSING}
            )
            if active >= settings.max_active_tasks:
                raise ServiceUnavailableError("Too many active tasks.")

            task = adapt_morpheus_request(raw)
            if task.callback_url:
                assert_safe_url(task.callback_url)
            self._by_id[task.task_id] = task
            self._by_external[task.external_task_id] = task.task_id
            return task, True

    async def claim_for_processing(self, task_id: str) -> tuple[InternalTask | None, bool]:
        """Return (task, claimed). Only one caller gets claimed=True."""
        async with self._lock:
            task = self._by_id.get(task_id)
            if not task:
                return None, False
            if task.status in {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.PROCESSING}:
                return task, False
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.now(timezone.utc)
            self._by_id[task.task_id] = task
            return task, True


store = TaskStore()


async def submit_task(raw: TaskSubmitRequest) -> InternalTask:
    settings = get_settings()
    if not settings.accepts_tasks:
        raise ServiceUnavailableError(
            f"Service state is {settings.service_state}; not accepting tasks."
        )
    task, _created = await store.create_or_get(raw)
    return task


async def process_task(task_id: str) -> InternalTask:
    task, claimed = await store.claim_for_processing(task_id)
    if not task:
        raise AgentError("INVALID_REQUEST", "Task not found.", status_code=404)
    if not claimed:
        return task

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
            "message": "An unexpected error occurred while processing the task.",
            "retryable": True,
        }
        logger.error(
            "task_failed",
            extra={"error_class": type(exc).__name__, "status": "failed"},
        )
        logger.exception("unhandled_task_exception: %s", exc)

    task.completed_at = datetime.now(timezone.utc)
    await store.save(task)
    return task


async def submit_and_process(raw: TaskSubmitRequest) -> InternalTask:
    task = await submit_task(raw)
    if task.status in {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.PROCESSING}:
        # Already finished, or another request owns processing.
        if task.status == TaskStatus.PROCESSING and task.result is None:
            # Best-effort: if we raced into PROCESSING owned by another coroutine
            # in the same process, wait briefly for completion.
            for _ in range(50):
                await asyncio.sleep(0.05)
                latest = await store.get(task.task_id)
                if latest and latest.status in {TaskStatus.SUCCESS, TaskStatus.FAILED}:
                    return latest
            return task
        return task
    return await process_task(task.task_id)
