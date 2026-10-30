"""
SafeGate — Headless OSI Protocol Server Daemon
==============================================
A pure network protocol server with NO web UI, NO HTML, and NO browser frontend.
Acts as a high-performance network security appliance screening media traffic
at Layers 1 through 7 of the OSI model.

COMMUNICATION:
- REST / Protocol Headers: Returns screening verdicts via HTTP headers (`X-SafeGate-Verdict`)
  and structured JSON telemetry.
- Fail-Closed: Outages, malformed payloads, or model exceptions return HTTP 403/400.
"""

import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, UploadFile, File, Header, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.db import init_db, get_db
from app.security.headers import SecurityHeadersMiddleware
from app.osi.stack import OSIProtocolStack
from app.pipeline.audit import verify_audit_chain

logger = logging.getLogger("safegate-osi-server")

stack = OSIProtocolStack()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SafeGate Headless OSI Protocol Server...")
    settings.quarantine_path.mkdir(parents=True, exist_ok=True)
    settings.review_path.mkdir(parents=True, exist_ok=True)
    settings.published_path.mkdir(parents=True, exist_ok=True)
    init_db()
    yield
    logger.info("SafeGate Headless Server stopped cleanly.")


app = FastAPI(
    title="SafeGate Headless OSI Security Server",
    description="7-Layer OSI Protocol Screening Appliance (No Web UI)",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(SecurityHeadersMiddleware)


@app.get("/health")
def health_check():
    return {
        "status": "online",
        "service": "SafeGate Headless OSI Server",
        "architecture": "7-Layer OSI Protocol Stack",
        "mode": "fail-closed",
    }


@app.post("/osi/scan", summary="Screen media stream across Layers 1-7")
async def scan_media_stream(
    request: Request,
    file: UploadFile = File(...),
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    """
    Ingests video payload and executes analysis through the complete 7-Layer OSI Stack:
    L1 Physical -> L2 Data Link -> L3 Network -> L4 Transport -> L5 Session -> L6 Presentation -> L7 Application.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()

    db: Session = next(get_db())
    try:
        report = stack.process_media_stream(
            stream=file.file,
            original_filename=file.filename or "unknown.mp4",
            client_ip=client_ip,
            session_key=x_api_key or "",
            db=db,
        )

        headers = {
            "X-SafeGate-Verdict": report.verdict,
            "X-SafeGate-Upload-Id": report.upload_id,
            "X-SafeGate-Latency": str(report.scan_duration_sec),
            "X-SafeGate-OSI-Layers": "L1-L7",
        }

        # Format layer diagnostics
        steps_summary = [
            {
                "layer": s.layer_num,
                "name": s.layer_name,
                "status": s.status,
                "latency_ms": round(s.duration_ms, 2),
                "details": s.details,
            }
            for s in report.steps
        ]

        return JSONResponse(
            status_code=200 if report.verdict == "ALLOW" else 403 if report.verdict == "BLOCK" else 202,
            content={
                "upload_id": report.upload_id,
                "verdict": report.verdict,
                "explanation": report.explanation,
                "scan_duration_sec": report.scan_duration_sec,
                "sha256": report.sha256_hash,
                "nsfw_worst_score": report.nsfw_worst_score,
                "deepfake_risk_score": report.deepfake_risk_score,
                "osi_layer_trace": steps_summary,
            },
            headers=headers,
        )
    finally:
        db.close()


@app.get("/osi/audit")
def audit_verification(x_api_key: str = Header(None, alias="X-API-Key")):
    """Verifies the integrity of the Layer 5 cryptographic audit chain."""
    if not x_api_key or x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin auth required.")

    db: Session = next(get_db())
    try:
        return verify_audit_chain(db)
    finally:
        db.close()
