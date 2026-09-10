"""FastAPI application entrypoint for local + Vercel."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app import __version__
from app.api import callbacks, health, tasks, verify
from app.core.config import get_settings
from app.core.exceptions import AgentError, error_body
from app.core.logging import get_logger, new_request_id, setup_logging

setup_logging()
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
    logger.info(
        "startup",
        extra={"status": "ok", "capability": ",".join(settings.mvp_capabilities)},
    )
    yield
    logger.info("shutdown", extra={"status": "ok"})


app = FastAPI(
    title="Web3Dev AI",
    description="Morpheus Protocol autonomous Web3 development agent",
    version=__version__,
    lifespan=lifespan,
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


@app.middleware("http")
async def request_context(request: Request, call_next):
    new_request_id()
    response = await call_next(request)
    return response


@app.exception_handler(AgentError)
async def agent_error_handler(_request: Request, exc: AgentError):
    return JSONResponse(status_code=exc.status_code, content=error_body(exc))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError):
    messages = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", []) if x != "body")
        messages.append(f"{loc}: {err.get('msg')}" if loc else str(err.get("msg")))
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
    return {
        "service": "web3dev-ai",
        "name": settings.agent_name,
        "version": settings.agent_version,
        "status": settings.service_state,
        "docs": "/docs",
        "endpoints": [
            "/health",
            "/morpheus/verify",
            "/capabilities",
            "/api/tasks",
            "/api/tasks/{task_id}",
            "/callbacks/morpheus",
            "/version",
        ],
    }


@app.get("/capabilities")
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
async def version():
    settings = get_settings()
    return {
        "service": "web3dev-ai",
        "version": settings.agent_version,
        "commit": settings.commit,
        "environment": settings.environment,
        "state": settings.service_state,
    }
