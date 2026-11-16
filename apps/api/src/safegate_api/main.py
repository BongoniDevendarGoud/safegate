"""
SafeGate API Main Application Entry Point.
Initializes FastAPI, attaches RFC 7807 error handlers, and mounts security middleware.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from safegate_api.config import settings
from safegate_api.database import Base, engine
from safegate_api.errors import (
    ErrorCode,
    ProblemDetails,
    SafeGateException,
)
from safegate_api.logging import (
    correlation_id_ctx,
    logger,
    setup_logging,
    tenant_id_ctx,
)
from safegate_api.moderation import router as moderation_router
from safegate_api.routes import router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown procedures."""
    setup_logging(level="DEBUG" if settings.debug else "INFO", json_output=True)
    logger.info("SafeGate Media-Integrity Firewall API starting up...")

    # For local/testing environments without external migration runners, ensure tables exist if DB is reachable
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        logger.warning(f"Database schema auto-creation skipped: {exc}")

    yield

    logger.info("SafeGate API shutting down...")
    await engine.dispose()


app = FastAPI(
    title="SafeGate Media-Integrity Firewall API",
    version="0.1.0",
    description="Real-time media screening middleware and API for host platforms.",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Injects or extracts tracing correlation ID and tenant context."""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    tenant_id = request.headers.get("X-Tenant-ID") or "default-tenant"

    corr_token = correlation_id_ctx.set(correlation_id)
    tenant_token = tenant_id_ctx.set(tenant_id)

    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    finally:
        correlation_id_ctx.reset(corr_token)
        tenant_id_ctx.reset(tenant_token)


# ---------------------------------------------------------
# RFC 7807 Error Handlers
# ---------------------------------------------------------


@app.exception_handler(SafeGateException)
async def safegate_exception_handler(request: Request, exc: SafeGateException) -> JSONResponse:
    """Handles domain-specific SafeGate firewall exceptions."""
    problem = exc.to_problem_details(
        instance=request.url.path,
        correlation_id=correlation_id_ctx.get(),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handles FastAPI Pydantic request validation errors."""
    problem = ProblemDetails(
        type="https://safegate.ai/errors/invalid_input",
        title="Invalid Request Parameters",
        status=422,
        detail="The request body or query parameters failed schema validation.",
        instance=request.url.path,
        code=ErrorCode.INVALID_INPUT,
        correlation_id=correlation_id_ctx.get(),
        invalid_params={"errors": exc.errors()},
    )
    return JSONResponse(
        status_code=422,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fail-closed handler for uncaught server exceptions."""
    logger.exception(f"Unhandled server exception on {request.url.path}: {exc}")
    problem = ProblemDetails(
        type="https://safegate.ai/errors/internal_error",
        title="Internal Firewall Error",
        status=500,
        detail="An unexpected internal error occurred. Content routed to fail-closed review.",
        instance=request.url.path,
        code=ErrorCode.INTERNAL_ERROR,
        correlation_id=correlation_id_ctx.get(),
    )
    return JSONResponse(
        status_code=500,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


# Mount API routes
app.include_router(router)
app.include_router(moderation_router)
