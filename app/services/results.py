"""Result helpers."""

from __future__ import annotations

from typing import Any

from app.models.task import InternalTask


def public_result(task: InternalTask) -> dict[str, Any]:
    return task.to_public()
