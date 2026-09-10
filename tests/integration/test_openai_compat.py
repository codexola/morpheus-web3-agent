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
async def test_v1_chat_completions_trailing_slash(client):
    r = await client.post(
        "/v1/chat/completions/",
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


@pytest.mark.asyncio
async def test_null_content_accepted(client):
    r = await client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": None}]},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_empty_messages_openai_error(client):
    r = await client.post("/v1/chat/completions", json={"messages": []})
    assert r.status_code == 400
    assert "error" in r.json()
    assert "message" in r.json()["error"]


@pytest.mark.asyncio
async def test_stream_sse(client):
    r = await client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "hi"}], "stream": True},
    )
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    assert "data:" in r.text
    assert "[DONE]" in r.text
