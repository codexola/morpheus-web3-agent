"""Integration tests against FastAPI app."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_verify(client):
    r = await client.get("/morpheus/verify")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "smart_contract_audit" in body["capabilities"]
    assert body["agent"]["online"] is True


@pytest.mark.asyncio
async def test_capabilities(client):
    r = await client.get("/capabilities")
    assert r.status_code == 200
    assert len(r.json()["capabilities"]) == 4


@pytest.mark.asyncio
async def test_smart_contract_task(client):
    src = open("tests/fixtures/vulnerable_vault.sol", encoding="utf-8").read()
    r = await client.post(
        "/api/tasks",
        json={
            "task_id": "ext_audit_1",
            "capability": "smart_contract_audit",
            "description": "Audit vault",
            "input": {"source_code": src, "chain": "ethereum"},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["result"]["report"]["summary"]["high"] >= 1

    # idempotency
    r2 = await client.post(
        "/api/tasks",
        json={
            "task_id": "ext_audit_1",
            "capability": "smart_contract_audit",
            "input": {"source_code": src},
        },
    )
    assert r2.json()["task_id"] == body["task_id"]


@pytest.mark.asyncio
async def test_code_review_task(client):
    r = await client.post(
        "/api/tasks",
        json={
            "capability": "code_security_review",
            "input": {
                "language": "python",
                "source_code": "import os\nos.system(user_input)\npassword = 'supersecret'\n",
            },
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"
    findings = r.json()["result"]["report"]["findings"]
    assert len(findings) >= 1


@pytest.mark.asyncio
async def test_research_task(client):
    r = await client.post(
        "/api/tasks",
        json={
            "capability": "web3_research",
            "description": "Research Uniswap v3 architecture",
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"
    assert "executive_summary" in r.json()["result"]


@pytest.mark.asyncio
async def test_unsupported_capability(client):
    r = await client.post(
        "/api/tasks",
        json={"capability": "time_travel", "description": "nope"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "failed"
    assert body["error"]["code"] == "UNSUPPORTED_CAPABILITY"
