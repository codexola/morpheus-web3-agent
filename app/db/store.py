"""Postgres-backed durable task store (Neon)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError
from app.core.security import assert_safe_url
from app.db.connection import dumps, get_pool
from app.models.task import InternalTask, TaskStatus, TaskSubmitRequest, adapt_morpheus_request


def _row_to_task(row) -> InternalTask:
    def _json(value):
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        return json.loads(value)

    return InternalTask(
        task_id=row["id"],
        external_task_id=row["external_task_id"],
        capability=row["capability"],
        description=row["description"] or "",
        input=_json(row["input"]) or {},
        callback_url=row["callback_url"],
        chain=row["chain"],
        metadata=_json(row["metadata"]) or {},
        status=TaskStatus(row["status"]),
        result=_json(row["result"]),
        error=_json(row["error"]),
        created_at=row["created_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        request_payload=_json(row["request_payload"]) or {},
    )


class PostgresTaskStore:
    async def get(self, task_id: str) -> InternalTask | None:
        pool = await get_pool()
        assert pool is not None
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)
            return _row_to_task(row) if row else None

    async def get_by_external(self, external_task_id: str) -> InternalTask | None:
        pool = await get_pool()
        assert pool is not None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tasks WHERE external_task_id = $1",
                external_task_id,
            )
            return _row_to_task(row) if row else None

    async def save(self, task: InternalTask) -> InternalTask:
        pool = await get_pool()
        assert pool is not None
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tasks (
                    id, external_task_id, capability, status, description, input,
                    callback_url, chain, metadata, request_payload, result, error,
                    created_at, started_at, completed_at
                ) VALUES (
                    $1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9::jsonb,$10::jsonb,$11::jsonb,$12::jsonb,
                    $13,$14,$15
                )
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    description = EXCLUDED.description,
                    input = EXCLUDED.input,
                    callback_url = EXCLUDED.callback_url,
                    chain = EXCLUDED.chain,
                    metadata = EXCLUDED.metadata,
                    request_payload = EXCLUDED.request_payload,
                    result = EXCLUDED.result,
                    error = EXCLUDED.error,
                    started_at = EXCLUDED.started_at,
                    completed_at = EXCLUDED.completed_at
                """,
                task.task_id,
                task.external_task_id,
                task.capability,
                task.status.value,
                task.description,
                dumps(task.input),
                task.callback_url,
                task.chain,
                dumps(task.metadata),
                dumps(task.request_payload),
                dumps(task.result) if task.result is not None else None,
                dumps(task.error) if task.error is not None else None,
                task.created_at,
                task.started_at,
                task.completed_at,
            )
            await conn.execute(
                """
                INSERT INTO task_events (task_id, event_type, detail)
                VALUES ($1, $2, $3::jsonb)
                """,
                task.task_id,
                f"status:{task.status.value}",
                dumps({"capability": task.capability}),
            )
        return task

    async def create_or_get(self, raw: TaskSubmitRequest) -> tuple[InternalTask, bool]:
        settings = get_settings()
        pool = await get_pool()
        assert pool is not None
        external = raw.external_task_id or raw.task_id or raw.id

        async with pool.acquire() as conn:
            async with conn.transaction():
                if external:
                    row = await conn.fetchrow(
                        "SELECT * FROM tasks WHERE external_task_id = $1 FOR UPDATE",
                        external,
                    )
                    if row:
                        return _row_to_task(row), False

                active = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM tasks
                    WHERE status = ANY($1::text[])
                    """,
                    [TaskStatus.ACCEPTED.value, TaskStatus.PROCESSING.value],
                )
                if int(active or 0) >= settings.max_active_tasks:
                    raise ServiceUnavailableError("Too many active tasks.")

                task = adapt_morpheus_request(raw)
                if task.callback_url:
                    assert_safe_url(task.callback_url)

                await conn.execute(
                    """
                    INSERT INTO tasks (
                        id, external_task_id, capability, status, description, input,
                        callback_url, chain, metadata, request_payload, created_at
                    ) VALUES (
                        $1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9::jsonb,$10::jsonb,$11
                    )
                    """,
                    task.task_id,
                    task.external_task_id,
                    task.capability,
                    task.status.value,
                    task.description,
                    dumps(task.input),
                    task.callback_url,
                    task.chain,
                    dumps(task.metadata),
                    dumps(task.request_payload),
                    task.created_at,
                )
                await conn.execute(
                    """
                    INSERT INTO task_events (task_id, event_type, detail)
                    VALUES ($1, 'created', $2::jsonb)
                    """,
                    task.task_id,
                    dumps({"external_task_id": task.external_task_id}),
                )
                return task, True

    async def claim_for_processing(
        self, task_id: str, *, stale_after_seconds: float = 90.0
    ) -> tuple[InternalTask | None, bool]:
        pool = await get_pool()
        assert pool is not None
        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "SELECT * FROM tasks WHERE id = $1 FOR UPDATE",
                    task_id,
                )
                if not row:
                    return None, False
                task = _row_to_task(row)
                now = datetime.now(timezone.utc)
                if task.status in {TaskStatus.SUCCESS, TaskStatus.FAILED}:
                    return task, False
                if task.status == TaskStatus.PROCESSING:
                    started = task.started_at or task.created_at
                    age = (now - started).total_seconds()
                    if age < stale_after_seconds:
                        return task, False
                await conn.execute(
                    """
                    UPDATE tasks
                    SET status = $2, started_at = $3
                    WHERE id = $1
                    """,
                    task_id,
                    TaskStatus.PROCESSING.value,
                    now,
                )
                task.status = TaskStatus.PROCESSING
                task.started_at = now
                return task, True
