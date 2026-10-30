"""
SafeGate — Upload API Route (Hardened with Auth, Rate Limiting & Audit)
========================================================================
Handles `POST /api/upload`:
1. Authenticates client using `X-API-Key` (`CLIENT_API_KEY`).
2. Enforces IP-based rate limiting via `slowapi`.
3. Ingests video payload via Stage 1 Intake.
4. Appends audit log entries for upload intake and final verdict.
5. Invokes the full screening pipeline via `run_pipeline`.
6. Returns comprehensive verdict (BLOCK, REVIEW, or ALLOW).

FAIL-CLOSED BEHAVIOR:
- Validation failure -> HTTP 422.
- Authentication failure -> HTTP 401 / 403.
- Rate limit exceeded -> HTTP 429.
- Processing failure -> HTTP 500 without stack traces; file safely quarantined in review/.
"""

import logging
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.config import settings
from app.db import get_db
from app.models.database import Upload
from app.models.schemas import UploadResponse, ErrorResponse
from app.security.auth import verify_client_api_key
from app.security.rate_limit import limiter
from app.pipeline.intake import save_upload
from app.pipeline.orchestrator import run_pipeline
from app.pipeline.audit import append_audit_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["upload"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Missing client API key"},
        403: {"model": ErrorResponse, "description": "Invalid client API key"},
        422: {"model": ErrorResponse, "description": "Validation failed (invalid MIME, size, or format)"},
        429: {"model": ErrorResponse, "description": "Rate limit quota exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Screen and ingest a video upload",
    description="Uploads a video to SafeGate. Authenticated via X-API-Key and screened through the fail-closed pipeline.",
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def upload_video(
    request: Request,
    file: UploadFile = File(..., description="Binary video file to screen"),
    db: Session = Depends(get_db),
    _client_key: str = Depends(verify_client_api_key),
):
    try:
        # Read raw bytes into memory
        upload_bytes = await file.read()
        if not upload_bytes:
            raise ValueError("Empty file submitted")

        original_name = file.filename or "upload.mp4"

        # Stage 1: Validation and atomic quarantine
        file_path, stored_name, orig_name, file_size = save_upload(
            upload_bytes=upload_bytes,
            original_filename=original_name,
        )

        # Create preliminary database record
        upload_record = Upload(
            original_filename=orig_name,
            stored_filename=stored_name,
            file_size=file_size,
            verdict="REVIEW",  # Initial fail-closed state
            explanation="Initial intake complete; screening pipeline in progress.",
        )
        db.add(upload_record)
        db.commit()
        db.refresh(upload_record)

        # Audit log event: intake received
        append_audit_log(
            action="upload_intake_received",
            details={
                "original_filename": orig_name,
                "file_size": file_size,
                "stored_filename": stored_name,
            },
            upload_id=upload_record.id,
            db=db,
        )

        # Run full screening pipeline (Stages 2 through 8)
        processed_record = run_pipeline(
            upload_id=upload_record.id,
            file_path=file_path,
            db=db,
        )

        # Audit log event: verdict determined
        append_audit_log(
            action=f"verdict_{processed_record.verdict.lower()}",
            details={
                "verdict": processed_record.verdict,
                "explanation": processed_record.explanation,
                "scan_duration_sec": processed_record.scan_duration_sec,
                "nsfw_worst_score": processed_record.nsfw_worst_score,
                "deepfake_risk_score": processed_record.deepfake_risk_score,
            },
            upload_id=processed_record.id,
            db=db,
        )

        return UploadResponse(
            upload_id=processed_record.id,
            verdict=processed_record.verdict,
            explanation=processed_record.explanation,
            scan_duration_sec=processed_record.scan_duration_sec,
            nsfw_worst_score=processed_record.nsfw_worst_score,
            deepfake_risk_score=processed_record.deepfake_risk_score,
        )

    except ValueError as val_err:
        logger.warning("Upload validation rejected: %s", val_err)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unhandled error during upload screening: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while screening the uploaded file. Fail-closed policy applied.",
        )
