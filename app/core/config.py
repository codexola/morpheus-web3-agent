"""Application configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ServiceState = Literal["RUNNING", "DEGRADED", "MAINTENANCE", "DISABLED"]

_DEFAULT_ETH = "https://ethereum.publicnode.com"
_DEFAULT_BASE = "https://mainnet.base.org"
_DEFAULT_ARB = "https://arb1.arbitrum.io/rpc"
_DEFAULT_POLYGON = "https://polygon-rpc.com"
_DEFAULT_SOLANA = "https://api.mainnet-beta.solana.com"


def _empty_as_none(value: Any) -> Any:
    """Treat blank env vars as unset so Field defaults still apply."""
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    agent_name: str = Field(default="Web3Dev AI", alias="AGENT_NAME")
    agent_version: str = Field(default="1.1.1", alias="AGENT_VERSION")
    agent_description: str = Field(
        default=(
            "Autonomous Web3 and AI development agent providing smart-contract "
            "security analysis, source-code security review, blockchain analytics, "
            "and Web3 research with structured developer-ready results."
        ),
        alias="AGENT_DESCRIPTION",
    )

    environment: str = Field(default="development", alias="ENVIRONMENT")
    service_state: ServiceState = Field(default="RUNNING", alias="SERVICE_STATE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    commit_sha: str = Field(default="", alias="COMMIT_SHA")
    vercel_git_commit_sha: str = Field(default="", alias="VERCEL_GIT_COMMIT_SHA")

    morpheus_shared_secret: str = Field(default="", alias="MORPHEUS_SHARED_SECRET")
    morpheus_api_url: str = Field(
        default="https://api.morpheusprotocol.dev",
        alias="MORPHEUS_API_URL",
    )
    callback_shared_secret: str = Field(default="", alias="CALLBACK_SHARED_SECRET")
    require_shared_secret: bool = Field(default=False, alias="REQUIRE_SHARED_SECRET")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    primary_model: str = Field(default="gpt-4o-mini", alias="PRIMARY_MODEL")
    secondary_model: str = Field(default="gpt-4o-mini", alias="SECONDARY_MODEL")
    fast_model: str = Field(default="gpt-4o-mini", alias="FAST_MODEL")
    reasoning_model: str = Field(default="gpt-4o", alias="REASONING_MODEL")

    database_url: str = Field(default="", alias="DATABASE_URL")
    postgres_url: str = Field(default="", alias="POSTGRES_URL")
    redis_url: str = Field(default="", alias="REDIS_URL")

    eth_rpc_url: str = Field(default=_DEFAULT_ETH, alias="ETH_RPC_URL")
    base_rpc_url: str = Field(default=_DEFAULT_BASE, alias="BASE_RPC_URL")
    arbitrum_rpc_url: str = Field(default=_DEFAULT_ARB, alias="ARBITRUM_RPC_URL")
    polygon_rpc_url: str = Field(default=_DEFAULT_POLYGON, alias="POLYGON_RPC_URL")
    solana_rpc_url: str = Field(default=_DEFAULT_SOLANA, alias="SOLANA_RPC_URL")

    max_agent_steps: int = Field(default=12, alias="MAX_AGENT_STEPS")
    max_tool_calls: int = Field(default=25, alias="MAX_TOOL_CALLS")
    max_llm_retries: int = Field(default=2, alias="MAX_LLM_RETRIES")
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    max_active_tasks: int = Field(default=10, alias="MAX_ACTIVE_TASKS")
    max_json_bytes: int = Field(default=2_097_152, alias="MAX_JSON_BYTES")

    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    payout_address: str = Field(default="", alias="PAYOUT_ADDRESS")

    rpc_timeout_seconds: float = 10.0
    http_timeout_seconds: float = 15.0
    llm_timeout_seconds: float = 60.0

    mvp_capabilities: tuple[str, ...] = (
        "smart_contract_audit",
        "code_security_review",
        "blockchain_analytics",
        "web3_research",
    )

    @field_validator("eth_rpc_url", mode="before")
    @classmethod
    def default_eth(cls, value: Any) -> Any:
        return _empty_as_none(value) or _DEFAULT_ETH

    @field_validator("base_rpc_url", mode="before")
    @classmethod
    def default_base(cls, value: Any) -> Any:
        return _empty_as_none(value) or _DEFAULT_BASE

    @field_validator("arbitrum_rpc_url", mode="before")
    @classmethod
    def default_arb(cls, value: Any) -> Any:
        return _empty_as_none(value) or _DEFAULT_ARB

    @field_validator("polygon_rpc_url", mode="before")
    @classmethod
    def default_polygon(cls, value: Any) -> Any:
        return _empty_as_none(value) or _DEFAULT_POLYGON

    @field_validator("solana_rpc_url", mode="before")
    @classmethod
    def default_solana(cls, value: Any) -> Any:
        return _empty_as_none(value) or _DEFAULT_SOLANA

    @field_validator(
        "openai_api_key",
        "database_url",
        "postgres_url",
        "redis_url",
        "morpheus_shared_secret",
        "callback_shared_secret",
        "sentry_dsn",
        mode="before",
    )
    @classmethod
    def blank_secret_to_empty(cls, value: Any) -> Any:
        return _empty_as_none(value) or ""

    @property
    def resolved_database_url(self) -> str:
        return self.database_url or self.postgres_url or ""

    @property
    def commit(self) -> str:
        return self.commit_sha or self.vercel_git_commit_sha or "local"

    @property
    def accepts_tasks(self) -> bool:
        return self.service_state == "RUNNING"

    @property
    def is_online(self) -> bool:
        return self.service_state in {"RUNNING", "DEGRADED"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
