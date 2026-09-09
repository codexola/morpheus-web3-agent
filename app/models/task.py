"""Task models — internal representation + Morpheus adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class TaskStatus(str, Enum):
    ACCEPTED = "accepted"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class Capability(str, Enum):
    SMART_CONTRACT_AUDIT = "smart_contract_audit"
    CODE_SECURITY_REVIEW = "code_security_review"
    BLOCKCHAIN_ANALYTICS = "blockchain_analytics"
    WEB3_RESEARCH = "web3_research"


class TaskSubmitRequest(BaseModel):
    """Inbound payload (Morpheus-compatible + flexible aliases)."""

    task_id: str | None = None
    external_task_id: str | None = None
    id: str | None = None
    capability: str
    description: str = ""
    input: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
    callback_url: str | None = None
    chain: str | None = None
    amount_usdt: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("capability")
    @classmethod
    def normalize_capability(cls, v: str) -> str:
        return (v or "").strip().lower().replace("-", "_").replace(" ", "_")


class InternalTask(BaseModel):
    task_id: str
    external_task_id: str
    capability: str
    description: str = ""
    input: dict[str, Any] = Field(default_factory=dict)
    callback_url: str | None = None
    chain: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.ACCEPTED
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    request_payload: dict[str, Any] = Field(default_factory=dict)

    def to_public(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "task_id": self.task_id,
            "external_task_id": self.external_task_id,
            "capability": self.capability,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }
        if self.started_at:
            body["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            body["completed_at"] = self.completed_at.isoformat()
        if self.result is not None:
            body["result"] = self.result
            body["success"] = self.status == TaskStatus.SUCCESS
        if self.error is not None:
            body["error"] = self.error
            body["success"] = False
        return body


def adapt_morpheus_request(raw: TaskSubmitRequest) -> InternalTask:
    """Convert Morpheus (or any) inbound schema into InternalTask."""
    external = raw.external_task_id or raw.task_id or raw.id or f"ext_{uuid4().hex[:12]}"
    merged_input: dict[str, Any] = {}
    if raw.payload:
        merged_input.update(raw.payload)
    if raw.data:
        merged_input.update(raw.data)
    merged_input.update(raw.input)
    if raw.chain and "chain" not in merged_input:
        merged_input["chain"] = raw.chain
    if raw.description and "description" not in merged_input:
        merged_input.setdefault("query", raw.description)

    return InternalTask(
        task_id=f"task_{uuid4().hex[:12]}",
        external_task_id=external,
        capability=raw.capability,
        description=raw.description,
        input=merged_input,
        callback_url=raw.callback_url,
        chain=raw.chain or merged_input.get("chain"),
        metadata=raw.metadata,
        request_payload=raw.model_dump(),
    )
