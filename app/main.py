"""
SafeGate — Main Application Entry Point (Security Hardened)
============================================================
Initializes the FastAPI application with:
1. Security Headers Middleware (CSP, HSTS, X-Frame-Options, X-Content-Type-Options).
2. Strict CORS Middleware restricted to DASHBOARD_ORIGIN.
3. IP-based Rate Limiter (slowapi).
4. Global Exception Handlers (suppressing stack traces).
5. Router Registration: Upload API and Audit Log Verification.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.db import init_db
from app.security.headers import SecurityHeadersMiddleware
from app.security.cors import configure_cors
from app.security.rate_limit import limiter, rate_limit_exceeded_handler
from app.routes.upload import router as upload_router
from app.routes.audit import router as audit_router
from app.routes.dashboard import router as dashboard_router
from app.routes.videos import router as video_router

# Configure structured application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("safegate")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager: verifies storage directories and SQLite schema.
    """
    logger.info("Initializing SafeGate fail-closed AI upload gateway...")

    # Ensure storage directories exist
    settings.quarantine_path.mkdir(parents=True, exist_ok=True)
    settings.review_path.mkdir(parents=True, exist_ok=True)
    settings.published_path.mkdir(parents=True, exist_ok=True)
    settings.frames_path.mkdir(parents=True, exist_ok=True)
    settings.reports_path.mkdir(parents=True, exist_ok=True)

    # Initialize SQLite database schema
    init_db()
    logger.info("Database and storage directories verified.")
    yield
    logger.info("SafeGate shutting down cleanly.")


app = FastAPI(
    title="SafeGate 2.0",
    description="AI-Powered Website Video Upload Firewall & Frame-Level Deepfake Detection System.",
    version="2.0.0",
    lifespan=lifespan,
)

# 1. Register Rate Limiter state and custom 429 handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# 2. Register Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# 3. Configure Strict CORS
configure_cors(app)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global catch-all exception handler suppressing internal stack traces.
    """
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error: processing failed safely."},
    )


# Register API routers
app.include_router(upload_router)
app.include_router(audit_router)
app.include_router(dashboard_router)
app.include_router(video_router)


@app.get("/health", summary="Health Check", tags=["system"])
async def health():
    """Returns basic system health status."""
    return {"status": "ok", "service": "safegate", "version": "0.1.0"}


# Serve static dashboard files
dashboard_path = Path(__file__).resolve().parent.parent / "dashboard"
dashboard_path.mkdir(parents=True, exist_ok=True)

index_file = dashboard_path / "index.html"
if not index_file.exists():
    index_file.write_text(
        "<!DOCTYPE html><html><head><title>SafeGate</title></head>"
        "<body><h1>SafeGate Upload Gateway</h1>"
        "<p>API documentation available at <a href='/docs'>/docs</a>.</p></body></html>",
        encoding="utf-8",
    )

app.mount("/", StaticFiles(directory=str(dashboard_path), html=True), name="dashboard")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
