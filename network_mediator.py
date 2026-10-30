"""
SafeGate — Transparent Internet Upload Mediator Gateway (Prototype)
====================================================================
Acts as the central network mediator between internet clients and destination servers.
In a real-world telecommunication architecture, this gateway sits at the:
- ISP Gateway (Clean Pipe architecture).
- Cloudflare / SASE Zero-Trust Inline Gateway.
- Corporate / Campus Next-Generation Firewall (NGFW).

HOW IT OPERATES AS THE INTERNET MEDIATOR:
1. Every client on the network sends upload requests through this mediator (Port 8080).
2. When a user tries to upload to ANY public platform (e.g., mock YouTube on port 9000):
   a. SafeGate intercepts the upload request in mid-air.
   b. It inspects the video payload through the complete 7-Layer OSI Security Stack:
      - Layer 1 (Physical): Bitstream quota & buffer bounds.
      - Layer 2 (Data Link): Video frame delineation & temporal sampling.
      - Layer 3 (Network): Origin IP rate limiting & traffic policing.
      - Layer 4 (Transport): SHA-256 cryptographic checksum against known blocklists.
      - Layer 5 (Session): Authenticates session credentials & logs to SHA-256 audit chain.
      - Layer 6 (Presentation): Magic-byte syntax parsing & DCT perceptual pHash deduplication.
      - Layer 7 (Application): Local Vision Transformer (Falconsai ViT) + Gemini Opinion + Deepfake Forensics.
3. VERDICT ENFORCEMENT:
   - If CLEAN (ALLOW): SafeGate relays the upload to the destination server. The video reaches the internet!
   - If MALICIOUS DEEPFAKE / EXPLICIT (BLOCK / REVIEW): SafeGate TERMINATES the connection in flight.
     Returns HTTP 403 Forbidden. The destination server on the internet NEVER receives the file!
"""

import sys
import io
import time
import logging
import urllib.request
import urllib.error
from urllib.parse import urlparse
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import settings
from app.db import SessionLocal, init_db
from app.osi.stack import OSIProtocolStack

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [INTERNET-MEDIATOR] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("safegate-mediator")

app = FastAPI(
    title="SafeGate Internet Mediator Gateway",
    description="Global transparent upload proxy screening web traffic through the 7-Layer OSI stack.",
    version="1.0.0",
)

osi_stack = OSIProtocolStack()


def is_video_payload(content_type: str, body: bytes) -> bool:
    """Detects whether an HTTP request contains video content."""
    if not body:
        return False
    ct = content_type.lower()
    if "video/" in ct:
        return True
    if "multipart/form-data" in ct:
        # Check for typical video signatures or filenames in multipart payload
        for ext in (b".mp4", b".mov", b".avi", b".mkv", b".webm"):
            if ext in body[:4096].lower():
                return True
        # Magic byte detection for MP4/MKV
        if b"ftyp" in body[:32] or b"\x1a\x45\xdf\xa3" in body[:32]:
            return True
    return False


def extract_filename_and_stream(body: bytes, content_type: str) -> tuple[str, io.BytesIO]:
    """Extracts raw media payload and filename from multipart stream."""
    import re
    match = re.search(rb'filename="([^"]+\.(?:mp4|mov|avi|mkv|webm))"', body, re.IGNORECASE)
    filename = match.group(1).decode("utf-8", errors="ignore") if match else "intercepted_upload.mp4"

    # If multipart, isolate the file section
    if b"\r\n\r\n" in body:
        parts = body.split(b"\r\n\r\n", 1)
        if len(parts) > 1:
            file_bytes = parts[1].rsplit(b"\r\n--", 1)[0]
            return filename, io.BytesIO(file_bytes)

    return filename, io.BytesIO(body)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
async def mediate_internet_traffic(request: Request, path: str):
    """
    Catch-all proxy endpoint that acts as the internet mediator.
    Intercepts and screens any media upload destined for any platform.
    """
    raw_body = await request.body()
    content_type = request.headers.get("content-type", "")
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Identify target destination URL (passed either via custom header, query param, or default mock platform)
    target_url = request.headers.get("X-Target-Destination")
    if not target_url:
        target_url = f"http://127.0.0.1:9000/{path}"
        if request.query_params:
            target_url += f"?{request.query_params}"

    logger.info("--> Intercepted traffic from client %s destined for %s", client_ip, target_url)

    # 1. Non-upload traffic: transparently relay without blocking
    if request.method.upper() != "POST" or not is_video_payload(content_type, raw_body):
        logger.info("Traffic is standard web traffic (non-media). Forwarding transparently.")
        return await forward_to_destination(request, target_url, raw_body, content_type)

    # 2. MEDIA UPLOAD DETECTED: Engage SafeGate 7-Layer OSI Security Stack
    filename, media_stream = extract_filename_and_stream(raw_body, content_type)
    stream_size = media_stream.getbuffer().nbytes

    logger.warning(
        "[MEDIATOR INTERCEPT] Intercepted video upload '%s' (%d bytes) headed to the internet (%s)!",
        filename,
        stream_size,
        target_url,
    )
    logger.info("[MEDIATOR SCREENING] Engaging SafeGate 7-Layer OSI Protocol Stack...")

    db = SessionLocal()
    try:
        report = osi_stack.process_media_stream(
            stream=media_stream,
            original_filename=filename,
            client_ip=client_ip,
            session_key=request.headers.get("X-API-Key", settings.CLIENT_API_KEY),
            db=db,
        )

        logger.info(
            "[MEDIATOR SCREENING RESULT] Verdict: %s | Latency: %.3fs | NSFW: %s | Deepfake: %s",
            report.verdict,
            report.scan_duration_sec,
            f"{report.nsfw_worst_score*100:.1f}%" if report.nsfw_worst_score is not None else "N/A",
            f"{report.deepfake_risk_score}/100" if report.deepfake_risk_score is not None else "N/A",
        )

        # ---------------------------------------------------------------------
        # ENFORCEMENT DECISION
        # ---------------------------------------------------------------------
        if report.verdict == "ALLOW":
            logger.info(
                "[MEDIATOR PERMITTED] Video '%s' passed all 7 OSI layers. Relaying payload to public internet platform...",
                filename,
            )
            # Forward payload to the real/mock destination server
            upstream_resp = await forward_to_destination(request, target_url, raw_body, content_type)
            # Add advisory mediator confirmation headers
            return upstream_resp

        # FAIL-CLOSED & THREAT NEUTRALIZATION: BLOCK or REVIEW
        logger.error(
            "[MEDIATOR BLOCKED] THREAT NEUTRALIZED! Video '%s' contains harmful deepfake or explicit content (%s). "
            "DROPPING CONNECTION in flight -- destination server will NEVER receive this file!",
            filename,
            report.verdict,
        )

        return JSONResponse(
            status_code=403,
            headers={
                "X-SafeGate-Mediator-Action": "BLOCKED_IN_TRANSIT",
                "X-SafeGate-Verdict": report.verdict,
                "X-SafeGate-Upload-ID": report.upload_id,
            },
            content={
                "error": "Blocked by SafeGate Global Internet Mediator",
                "status": "FORBIDDEN",
                "policy_verdict": report.verdict,
                "target_destination": target_url,
                "explanation": report.explanation,
                "deepfake_risk_score": f"{report.deepfake_risk_score}/100" if report.deepfake_risk_score is not None else "N/A",
                "nsfw_score": f"{report.nsfw_worst_score*100:.1f}%" if report.nsfw_worst_score is not None else "N/A",
                "security_guarantee": "This upload was intercepted and destroyed in flight. It has NOT reached the internet.",
            },
        )

    finally:
        db.close()


async def forward_to_destination(request: Request, target_url: str, body: bytes, content_type: str) -> Response:
    """Relays permitted packets upstream to the actual internet destination server."""
    req = urllib.request.Request(
        target_url,
        data=body if body else None,
        headers={"Content-Type": content_type} if content_type else {},
        method=request.method,
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_bytes = resp.read()
            return Response(
                content=resp_bytes,
                status_code=resp.getcode(),
                headers={
                    "Content-Type": resp.headers.get("Content-Type", "application/json"),
                    "X-SafeGate-Mediated": "PASSED_CLEAN",
                },
            )
    except urllib.error.HTTPError as err:
        return Response(content=err.read(), status_code=err.code)
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"detail": f"SafeGate Mediator failed to reach destination server: {exc}"},
        )


if __name__ == "__main__":
    init_db()
    print("======================================================================")
    print("  SafeGate Global Upload Mediator Gateway (Prototype)")
    print("======================================================================")
    print("Listening on: http://127.0.0.1:8080")
    print("Mediating uploads destined for Internet Platforms (e.g. port 9000)")
    print("Enforcement: Fail-Closed 7-Layer OSI Content & Deepfake Inspection")
    print("======================================================================\n")
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="warning")
