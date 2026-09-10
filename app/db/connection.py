"""Neon Postgres connection pool and schema bootstrap."""

from __future__ import annotations

import json
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    external_task_id TEXT NOT NULL,
    capability TEXT NOT NULL,
    status TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    input JSONB NOT NULL DEFAULT '{}'::jsonb,
    callback_url TEXT,
    chain TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    request_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB,
    error JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_tasks_external_task_id
    ON tasks (external_task_id);

CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS ix_tasks_created_at ON tasks (created_at DESC);

CREATE TABLE IF NOT EXISTS task_events (
    id BIGSERIAL PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_task_events_task_id ON task_events (task_id);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    request_id TEXT,
    task_id TEXT,
    capability TEXT,
    status TEXT,
    duration_ms INTEGER,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at DESC);

CREATE TABLE IF NOT EXISTS usage_stats (
    id BIGSERIAL PRIMARY KEY,
    capability TEXT NOT NULL,
    status TEXT NOT NULL,
    tokens INTEGER DEFAULT 0,
    cost_usd NUMERIC(12, 6) DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

_pool = None


def database_url() -> str:
    settings = get_settings()
    return (settings.resolved_database_url or "").strip()


def db_enabled() -> bool:
    return bool(database_url())


async def get_pool():
    global _pool
    if _pool is not None:
        return _pool
    url = database_url()
    if not url:
        return None
    import asyncpg

    _pool = await asyncpg.create_pool(
        dsn=url,
        min_size=1,
        max_size=5,
        command_timeout=15,
        statement_cache_size=0,
    )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def init_schema() -> bool:
    pool = await get_pool()
    if pool is None:
        logger.info("database_disabled")
        return False
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    logger.info("database_schema_ready", extra={"status": "ok"})
    return True


async def ping() -> bool:
    pool = await get_pool()
    if pool is None:
        return False
    async with pool.acquire() as conn:
        return (await conn.fetchval("SELECT 1")) == 1


def dumps(value: Any) -> str:
    return json.dumps(value if value is not None else {}, default=str)


async def write_audit(
    *,
    request_id: str | None,
    task_id: str | None,
    capability: str | None,
    status: str | None,
    duration_ms: int | None = None,
    detail: dict | None = None,
) -> None:
    pool = await get_pool()
    if pool is None:
        return
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO audit_logs (request_id, task_id, capability, status, duration_ms, detail)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            """,
            request_id,
            task_id,
            capability,
            status,
            duration_ms,
            dumps(detail or {}),
        )
