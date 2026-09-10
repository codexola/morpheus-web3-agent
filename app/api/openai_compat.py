"""OpenAI-compatible API for Morpheus Arena / verified endpoint tests."""

from __future__ import annotations

import json
import os
import secrets
import time
import uuid
from typing import Any

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings
from app.llm.client import get_llm

router = APIRouter(tags=["openai-compat"])

DEFAULT_MODEL = "web3dev-ai"


class ChatMessage(BaseModel):
    role: str
    content: str | list[Any] | None = ""

    @field_validator("content", mode="before")
    @classmethod
    def coerce_null_content(cls, value: Any) -> Any:
        return "" if value is None else value


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    temperature: float | None = 0.2
    max_tokens: int | None = None
    stream: bool | None = False


def openai_error(
    message: str,
    *,
    status_code: int = 400,
    err_type: str = "invalid_request_error",
    code: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message,
                "type": err_type,
                "param": None,
                "code": code,
            }
        },
    )


def _message_text(content: str | list[Any] | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and item.get("type") == "text":
            parts.append(str(item.get("text") or ""))
    return "\n".join(parts)


def _expected_api_key() -> str:
    settings = get_settings()
    return (os.getenv("ARENA_API_KEY") or settings.morpheus_shared_secret or "").strip()


def _extract_token(
    authorization: str | None,
    api_key: str | None,
    x_api_key: str | None,
) -> str | None:
    if authorization:
        parts = authorization.strip().split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        # Some clients send raw token in Authorization
        if len(parts) == 1:
            return parts[0].strip()
    for candidate in (api_key, x_api_key):
        if candidate and candidate.strip():
            return candidate.strip()
    return None


def _require_optional_auth(
    authorization: str | None = None,
    api_key: str | None = None,
    x_api_key: str | None = None,
) -> JSONResponse | None:
    expected = _expected_api_key()
    if not expected:
        return None
    provided = _extract_token(authorization, api_key, x_api_key)
    if not provided:
        return openai_error(
            "Missing authentication. Provide Authorization: Bearer <token> or api-key.",
            status_code=401,
            err_type="invalid_request_error",
            code="invalid_api_key",
        )
    if not secrets.compare_digest(provided, expected):
        return openai_error(
            "Invalid authentication credentials.",
            status_code=401,
            err_type="invalid_request_error",
            code="invalid_api_key",
        )
    return None


async def _generate_content(body: ChatCompletionRequest) -> tuple[str, str]:
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

    llm = get_llm()
    if llm.available:
        try:
            from openai import AsyncOpenAI

            settings = get_settings()
            client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.llm_timeout_seconds,
                max_retries=settings.max_llm_retries,
            )
            kwargs: dict[str, Any] = {
                "model": settings.fast_model or settings.primary_model,
                "temperature": body.temperature if body.temperature is not None else 0.2,
                "messages": [
                    {"role": "system", "content": system_extra},
                    *[
                        {"role": m.role, "content": _message_text(m.content)}
                        for m in body.messages
                        if m.role != "system"
                    ],
                ],
            }
            if body.max_tokens:
                kwargs["max_tokens"] = body.max_tokens
            resp = await client.chat.completions.create(**kwargs)
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
    return model, content


def _completion_payload(model: str, content: str, prompt_len: int) -> dict[str, Any]:
    return {
        "id": f"chatcmpl_{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
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


async def create_chat_completion(
    body: ChatCompletionRequest,
    *,
    authorization: str | None = None,
    api_key: str | None = None,
    x_api_key: str | None = None,
) -> dict[str, Any] | JSONResponse | StreamingResponse:
    auth_err = _require_optional_auth(authorization, api_key, x_api_key)
    if auth_err is not None:
        return auth_err
    if not body.messages:
        return openai_error("messages is required", code="invalid_request_error")

    prompt_len = sum(len(_message_text(m.content)) for m in body.messages)
    model, content = await _generate_content(body)

    if body.stream:
        completion_id = f"chatcmpl_{uuid.uuid4().hex[:24]}"
        created = int(time.time())

        async def event_stream():
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": content},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            done = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(done)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return _completion_payload(model, content, prompt_len)


@router.get("/v1/models")
@router.get("/v1/models/")
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
@router.post("/v1/chat/completions/")
async def chat_completions(
    body: ChatCompletionRequest,
    authorization: str | None = Header(default=None),
    api_key: str | None = Header(default=None, alias="api-key"),
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    return await create_chat_completion(
        body, authorization=authorization, api_key=api_key, x_api_key=x_api_key
    )


@router.post("/chat/completions")
@router.post("/chat/completions/")
async def chat_completions_alias(
    body: ChatCompletionRequest,
    authorization: str | None = Header(default=None),
    api_key: str | None = Header(default=None, alias="api-key"),
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    return await create_chat_completion(
        body, authorization=authorization, api_key=api_key, x_api_key=x_api_key
    )
