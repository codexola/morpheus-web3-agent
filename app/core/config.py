"""Application configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ServiceState = Literal["RUNNING", "DEGRADED", "MAINTENANCE", "DISABLED"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    agent_name: str = Field(default="Web3Dev AI", alias="AGENT_NAME")
    agent_version: str = Field(default="1.0.0", alias="AGENT_VERSION")
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

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    primary_model: str = Field(default="gpt-4o-mini", alias="PRIMARY_MODEL")
    secondary_model: str = Field(default="gpt-4o-mini", alias="SECONDARY_MODEL")
    fast_model: str = Field(default="gpt-4o-mini", alias="FAST_MODEL")
    reasoning_model: str = Field(default="gpt-4o", alias="REASONING_MODEL")

    database_url: str = Field(default="", alias="DATABASE_URL")
    redis_url: str = Field(default="", alias="REDIS_URL")

    eth_rpc_url: str = Field(default="https://ethereum.publicnode.com", alias="ETH_RPC_URL")
    base_rpc_url: str = Field(default="https://mainnet.base.org", alias="BASE_RPC_URL")
    arbitrum_rpc_url: str = Field(
        default="https://arb1.arbitrum.io/rpc",
        alias="ARBITRUM_RPC_URL",
    )
    polygon_rpc_url: str = Field(
        default="https://polygon-rpc.com",
        alias="POLYGON_RPC_URL",
    )
    solana_rpc_url: str = Field(
        default="https://api.mainnet-beta.solana.com",
        alias="SOLANA_RPC_URL",
    )

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
    llm_timeout_seconds: float = 90.0

    mvp_capabilities: tuple[str, ...] = (
        "smart_contract_audit",
        "code_security_review",
        "blockchain_analytics",
        "web3_research",
    )

    @property
    def commit(self) -> str:
        return self.commit_sha or self.vercel_git_commit_sha or "local"

    @property
    def accepts_tasks(self) -> bool:
        return self.service_state == "RUNNING"


@lru_cache
def get_settings() -> Settings:
    return Settings()
