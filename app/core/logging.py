"""Structured logging helpers."""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

from app.core.config import get_settings

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")
task_id_ctx: ContextVar[str] = ContextVar("task_id", default="")

_SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "openai_api_key",
    "private_key",
    "seed",
    "mnemonic",
    "password",
    "secret",
    "token",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get() or None,
            "task_id": task_id_ctx.get() or None,
        }
        for key in ("capability", "duration_ms", "status", "model", "token_usage", "error_class"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))


def new_request_id() -> str:
    rid = f"req_{uuid.uuid4().hex[:10]}"
    request_id_ctx.set(rid)
    return rid


def redact(data: Any) -> Any:
    if isinstance(data, dict):
        out = {}
        for k, v in data.items():
            if str(k).lower() in _SENSITIVE_KEYS or any(
                s in str(k).lower() for s in ("private", "secret", "seed", "mnemonic")
            ):
                out[k] = "[REDACTED]"
            else:
                out[k] = redact(v)
        return out
    if isinstance(data, list):
        return [redact(i) for i in data]
    return data


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
