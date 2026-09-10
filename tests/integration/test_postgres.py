"""Postgres-backed task persistence tests (skipped without DATABASE_URL)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

ROOT = Path(__file__).resolve().parents[2]


def _load_env_local() -> None:
    path = ROOT / ".env.local"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_local()

pytestmark = pytest.mark.skipif(
    not (os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")),
    reason="DATABASE_URL not configured",
)


@pytest.fixture
async def client():
    from app.core.config import get_settings
    from app.db.connection import close_pool, init_schema
    from app.main import app

    get_settings.cache_clear()
    await close_pool()
    await init_schema()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await close_pool()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_postgres_task_roundtrip(client):
    r = await client.post(
        "/api/tasks",
        json={
            "task_id": "pg_research_roundtrip_1",
            "capability": "web3_research",
            "description": "Postgres durability check",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    task_id = body["task_id"]

    g = await client.get(f"/api/tasks/{task_id}")
    assert g.status_code == 200
    assert g.json()["task_id"] == task_id

    # idempotency
    r2 = await client.post(
        "/api/tasks",
        json={
            "task_id": "pg_research_roundtrip_1",
            "capability": "web3_research",
            "description": "Postgres durability check",
        },
    )
    assert r2.json()["task_id"] == task_id


@pytest.mark.asyncio
async def test_health_reports_database(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["database"] == "ok"
