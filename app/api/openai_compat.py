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
from app.llm.prompts import SYSTEM_GUARDRAILS

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
    user_bits: list[str] = []
    system_bits: list[str] = [SYSTEM_GUARDRAILS]
    for msg in body.messages:
        text = _message_text(msg.content).strip()
        if not text:
            continue
        if msg.role == "system":
            system_bits.append(text)
        else:
            user_bits.append(f"{msg.role}: {text}")

    prompt = "\n\n".join(user_bits) or "Hello"
    system_extra = "\n\n".join(system_bits[1:]) if len(system_bits) > 1 else (
        "You are Web3Dev AI, a helpful Web3 development and security assistant. "
        "Answer clearly and technically."
    )

    llm = get_llm()
    if llm.available:
        try:
            content = await llm.complete(
                user_content=prompt,
                system_extra=system_extra,
                model=None,
                temperature=body.temperature if body.temperature is not None else 0.2,
            )
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
            "prompt_tokens": max(1, len(prompt) // 4),
            "completion_tokens": max(1, len(content) // 4),
            "total_tokens": max(2, (len(prompt) + len(content)) // 4),
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
