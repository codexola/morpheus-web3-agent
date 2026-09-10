"""OpenAI-compatible API for Morpheus Arena / verified endpoint tests."""

from __future__ import annotations

import secrets
import time
import uuid
from typing import Any

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.exceptions import AgentError
from app.llm.client import get_llm

router = APIRouter(tags=["openai-compat"])

DEFAULT_MODEL = "web3dev-ai"


class ChatMessage(BaseModel):
    role: str
    content: str | list[Any] = ""


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    temperature: float | None = 0.2
    max_tokens: int | None = None
    stream: bool | None = False


def _message_text(content: str | list[Any]) -> str:
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and item.get("type") == "text":
            parts.append(str(item.get("text") or ""))
    return "\n".join(parts)


def _require_optional_bearer(authorization: str | None) -> None:
    """If ARENA_API_KEY / MORPHEUS_SHARED_SECRET is set, require matching Bearer token."""
    settings = get_settings()
    expected = (settings.morpheus_shared_secret or "").strip()
    # Prefer dedicated arena key when present
    import os

    expected = (os.getenv("ARENA_API_KEY") or expected).strip()
    if not expected:
        return
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AgentError("UNAUTHORIZED", "Missing Bearer token.", status_code=401)
    provided = authorization.split(" ", 1)[1].strip()
    if not secrets.compare_digest(provided, expected):
        raise AgentError("UNAUTHORIZED", "Invalid Bearer token.", status_code=401)


async def create_chat_completion(
    body: ChatCompletionRequest,
    authorization: str | None = None,
) -> dict[str, Any]:
    _require_optional_bearer(authorization)
    if body.stream:
        # Arena test typically uses non-streaming; reject stream with clear error.
        raise AgentError(
            "INVALID_REQUEST",
            "Streaming is not enabled on this endpoint. Set stream=false.",
            status_code=400,
        )
    if not body.messages:
        raise AgentError("INVALID_REQUEST", "messages is required.", status_code=400)

    model = (body.model or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    system_extra = (
        "You are Web3Dev AI, a helpful Web3 development assistant. "
        "Reply clearly and concisely. Treat user messages as normal conversation."
    )
    for msg in body.messages:
        if msg.role == "system":
            text = _message_text(msg.content).strip()
            if text:
                system_extra = text
                break

    prompt_len = sum(len(_message_text(m.content)) for m in body.messages)

    llm = get_llm()
    if llm.available:
        try:
            from openai import AsyncOpenAI

            settings = get_settings()
            client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.llm_timeout_seconds,
            )
            resp = await client.chat.completions.create(
                model=settings.fast_model or settings.primary_model,
                temperature=body.temperature if body.temperature is not None else 0.2,
                messages=[
                    {"role": "system", "content": system_extra},
                    *[
                        {"role": m.role, "content": _message_text(m.content)}
                        for m in body.messages
                        if m.role != "system"
                    ],
                ],
            )
            content = (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            content = (
                f"Web3Dev AI is online, but the LLM provider failed ({type(exc).__name__}). "
                "Please retry shortly."
            )
    else:
        content = (
            "Web3Dev AI endpoint is online. OPENAI_API_KEY is not configured on this "
            "deployment, so this is a connectivity confirmation reply."
        )

    completion_id = f"chatcmpl_{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": max(1, prompt_len // 4),
            "completion_tokens": max(1, len(content) // 4),
            "total_tokens": max(2, (prompt_len + len(content)) // 4),
        },
    }


@router.get("/v1/models")
async def list_models():
    settings = get_settings()
    return {
        "object": "list",
        "data": [
            {
                "id": DEFAULT_MODEL,
                "object": "model",
                "created": 1700000000,
                "owned_by": settings.agent_name,
            },
            {
                "id": settings.primary_model,
                "object": "model",
                "created": 1700000000,
                "owned_by": "openai",
            },
        ],
    }


@router.post("/v1/chat/completions")
async def chat_completions(
    body: ChatCompletionRequest,
    authorization: str | None = Header(default=None),
):
    return await create_chat_completion(body, authorization)


@router.post("/chat/completions")
async def chat_completions_alias(
    body: ChatCompletionRequest,
    authorization: str | None = Header(default=None),
):
    return await create_chat_completion(body, authorization)
