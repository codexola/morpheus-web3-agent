"""FastAPI application entrypoint for local + Vercel."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app import __version__
from app.api import callbacks, health, openai_compat, tasks, verify
from app.api.openai_compat import ChatCompletionRequest, create_chat_completion
from app.core.config import get_settings
from app.core.exceptions import AgentError, error_body
from app.core.logging import get_logger, new_request_id, setup_logging
from app.core.sentry import init_sentry

# Sentry must initialize before the FastAPI app is constructed.
setup_logging()
init_sentry()
logger = get_logger(__name__)


class PayloadSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit():
            if int(content_length) > settings.max_json_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "success": False,
                        "error": {
                            "code": "INVALID_REQUEST",
                            "message": "Payload exceeds size limit.",
                            "retryable": False,
                        },
                    },
                )
        return await call_next(request)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    from app.db.connection import close_pool, db_enabled, init_schema

    if db_enabled():
        try:
            await init_schema()
        except Exception as exc:
            logger.error(
                "database_schema_failed",
                extra={"error_class": type(exc).__name__, "status": "error"},
            )
    logger.info(
        "startup",
        extra={"status": "ok", "capability": ",".join(settings.mvp_capabilities)},
    )
    yield
    await close_pool()
    logger.info("shutdown", extra={"status": "ok"})


app = FastAPI(
    title="Web3Dev AI",
    description="Morpheus Protocol autonomous Web3 development agent",
    version=__version__,
    lifespan=lifespan,
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(PayloadSizeLimitMiddleware)

app.include_router(health.router)
app.include_router(verify.router)
app.include_router(tasks.router)
app.include_router(callbacks.router)
app.include_router(openai_compat.router)


@app.middleware("http")
async def request_context(request: Request, call_next):
    new_request_id()
    response = await call_next(request)
    return response


@app.exception_handler(AgentError)
async def agent_error_handler(_request: Request, exc: AgentError):
    return JSONResponse(status_code=exc.status_code, content=error_body(exc))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    path = request.url.path
    messages = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", []) if x != "body")
        messages.append(f"{loc}: {err.get('msg')}" if loc else str(err.get("msg")))
    # OpenAI-shaped errors for Arena chat routes
    if path in {"/", "/v1/chat/completions", "/v1/chat/completions/", "/chat/completions", "/chat/completions/"}:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": "; ".join(messages) or "Request validation failed.",
                    "type": "invalid_request_error",
                    "param": None,
                    "code": None,
                }
            },
        )
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "INVALID_REQUEST",
                "message": "; ".join(messages) or "Request validation failed.",
                "retryable": False,
            },
        },
    )


@app.get("/")
async def root():
    settings = get_settings()
    endpoints = [
        "/health",
        "/morpheus/verify",
        "/capabilities",
        "/api/tasks",
        "/api/tasks/{task_id}",
        "/callbacks/morpheus",
        "/version",
        "/v1/models",
        "/v1/chat/completions",
    ]
    if settings.environment != "production":
        endpoints.append("/sentry-debug")
    return {
        "service": "web3dev-ai",
        "name": settings.agent_name,
        "version": settings.agent_version,
        "status": settings.service_state,
        "docs": "/docs",
        "openai_compatible": True,
        "endpoints": endpoints,
    }


@app.post("/")
async def root_chat_completions(
    body: ChatCompletionRequest,
    authorization: str | None = Header(default=None),
    api_key: str | None = Header(default=None, alias="api-key"),
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    """Morpheus Arena OPENAI format posts to the endpoint root → avoid HTTP 405."""
    return await create_chat_completion(
        body, authorization=authorization, api_key=api_key, x_api_key=x_api_key
    )


@app.get("/sentry-debug")
async def sentry_debug():
    """Intentional error for Sentry verification — disabled in production."""
    settings = get_settings()
    if settings.environment == "production":
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Not found.",
                    "retryable": False,
                },
            },
        )
    my_undefined_function()  # noqa: F821


@app.get("/capabilities")
@app.get("/capabilities/")
async def capabilities():
    settings = get_settings()
    catalog = {
        "smart_contract_audit": {
            "id": "smart_contract_audit",
            "name": "Smart Contract Audit",
            "description": (
                "Automated Solidity security analysis combining static vulnerability-pattern "
                "detection and optional contextual AI review with severity-ranked findings."
            ),
        },
        "code_security_review": {
            "id": "code_security_review",
            "name": "Code Security Review",
            "description": (
                "Security-oriented source analysis for Python, JavaScript, TypeScript, Java, "
                "and Solidity covering common vulnerabilities, secrets, and remediation."
            ),
        },
        "blockchain_analytics": {
            "id": "blockchain_analytics",
            "name": "Blockchain Analytics",
            "description": (
                "On-chain analysis of native balances, contract detection, and transactions "
                "across Ethereum, Base, Arbitrum, Polygon, and Solana."
            ),
        },
        "web3_research": {
            "id": "web3_research",
            "name": "Web3 Research",
            "description": (
                "Technical Web3 and DeFi research covering protocol architecture, token "
                "mechanics, risks, and relevant sources."
            ),
        },
    }
    return {
        "agent": settings.agent_name,
        "capabilities": [catalog[c] for c in settings.mvp_capabilities if c in catalog],
    }


@app.get("/version")
@app.get("/version/")
async def version():
    settings = get_settings()
    from app.core.sentry import _initialized as sentry_on
    from app.db.connection import db_enabled

    return {
        "service": "web3dev-ai",
        "version": settings.agent_version,
        "commit": settings.commit,
        "environment": settings.environment,
        "state": settings.service_state,
        "database": "neon" if db_enabled() else "memory",
        "sentry": "enabled" if sentry_on else "disabled",
        "openai": "configured" if bool(settings.openai_api_key) else "missing",
    }
