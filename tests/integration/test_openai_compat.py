"""OpenAI-compatible Arena endpoint tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_post_root_chat_completions(client):
    r = await client.post(
        "/",
        json={
            "model": "web3dev-ai",
            "messages": [{"role": "user", "content": "ping"}],
            "stream": False,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert body["choices"][0]["message"]["content"]


@pytest.mark.asyncio
async def test_v1_chat_completions(client):
    r = await client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hello"}]},
    )
    assert r.status_code == 200
    assert r.json()["object"] == "chat.completion"


@pytest.mark.asyncio
async def test_v1_models(client):
    r = await client.get("/v1/models")
    assert r.status_code == 200
    assert r.json()["object"] == "list"
    assert any(m["id"] == "web3dev-ai" for m in r.json()["data"])
