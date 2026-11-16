"""
SafeGate Core API Route Endpoints.
Implements intake, status polling, and audit verification.
"""

from __future__ import annotations

import io
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from safegate_api.audit import record_audit_event, verify_ledger_integrity
from safegate_api.config import settings
from safegate_api.database import get_db_session
from safegate_api.errors import ErrorCode, SafeGateException
from safegate_api.intake import validate_and_hash_stream
from safegate_api.logging import logger, upload_id_ctx
from safegate_api.models import MediaUpload
from safegate_api.schemas import (
    AuditVerifyResponse,
    FrameScoreSummary,
    HealthCheckResponse,
    UploadResponse,
    UploadStatusResponse,
)
from safegate_api.storage import StorageClient

router = APIRouter(prefix="/v1", tags=["Media Firewall"])

# Storage client instance
storage_client = StorageClient(config=settings.storage)


async def _background_process_upload(upload_id: str, quarantine_key: str, tenant_id: str) -> None:
    """Dispatches media processing asynchronously upon upload ingestion."""
    from safegate_api.database import async_session_factory
    from safegate_worker.processor import MediaProcessor

    try:
        processor = MediaProcessor(storage_client=storage_client)
        temp_path = storage_client.download_to_temp(quarantine_key)
        async with async_session_factory() as session:
            await processor.process_media_file(
                media_path=temp_path,
                upload_id=upload_id,
                session=session,
                tenant_id=tenant_id,
            )
            await session.commit()
        temp_path.unlink(missing_ok=True)
    except Exception as exc:
        logger.error(f"Background processing failed for upload {upload_id}: {exc}")


@router.post(
    "/media/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest media for pre-publish integrity screening",
)
async def upload_media(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default-tenant",
    db: AsyncSession = Depends(get_db_session),
) -> UploadResponse:
    """
    Ingests binary media, validates magic bytes, isolates file in quarantine,
    and enters an immutable audit trail entry.
    """
    upload_id = str(uuid.uuid4())
    upload_id_ctx.set(upload_id)

    raw_bytes = await file.read()
    if not raw_bytes:
        raise SafeGateException(
            message="Uploaded file is empty",
            code=ErrorCode.INVALID_INPUT,
            status_code=400,
            detail="File content has length 0 bytes.",
        )

    # 1. Intake validation & hashing
    meta = validate_and_hash_stream(
        stream=io.BytesIO(raw_bytes),
        max_size_bytes=settings.limits.max_video_size_bytes
        if file.content_type and "video" in file.content_type
        else settings.limits.max_image_size_bytes,
    )

    # 2. Put into storage quarantine
    quarantine_key = f"{x_tenant_id}/{upload_id}/{file.filename or 'media.bin'}"
    storage_client.upload_quarantine(
        key=quarantine_key,
        data=raw_bytes,
        content_type=meta.mime_type,
        metadata={"sha256": meta.sha256_hash, "tenant": x_tenant_id},
    )

    # 3. Create database entry
    media_entry = MediaUpload(
        id=upload_id,
        tenant_id=x_tenant_id,
        filename=file.filename or "media.bin",
        file_size_bytes=meta.size_bytes,
        mime_type=meta.mime_type,
        sha256_hash=meta.sha256_hash,
        is_video=meta.is_video,
        status="QUEUED",
        verdict="PENDING",
        quarantine_key=quarantine_key,
    )
    db.add(media_entry)

    # 4. Append to tamper-evident audit ledger
    await record_audit_event(
        session=db,
        event_type="MEDIA_INGESTED",
        tenant_id=x_tenant_id,
        upload_id=upload_id,
        payload={
            "filename": file.filename,
            "mime_type": meta.mime_type,
            "size_bytes": meta.size_bytes,
            "sha256": meta.sha256_hash,
            "quarantine_key": quarantine_key,
        },
    )

    logger.info(
        f"Media ingested successfully into quarantine: {upload_id} (SHA-256: {meta.sha256_hash[:12]}...)"
    )

    # Enqueue background integrity analysis
    background_tasks.add_task(
        _background_process_upload,
        upload_id=upload_id,
        quarantine_key=quarantine_key,
        tenant_id=x_tenant_id,
    )

    return UploadResponse(
        upload_id=upload_id,
        tenant_id=x_tenant_id,
        filename=file.filename or "media.bin",
        mime_type=meta.mime_type,
        file_size_bytes=meta.size_bytes,
        sha256_hash=meta.sha256_hash,
        status="QUEUED",
        verdict="PENDING",
        message="Media quarantined and enqueued for per-frame integrity analysis.",
    )


@router.get(
    "/media/{upload_id}",
    response_model=UploadStatusResponse,
    summary="Get status, verdict, and per-frame screening evidence",
)
async def get_media_status(
    upload_id: str,
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default-tenant",
    db: AsyncSession = Depends(get_db_session),
) -> UploadStatusResponse:
    """
    Retrieves current firewall status, content verdict, and per-frame forensic scores.
    """
    stmt = (
        select(MediaUpload)
        .where(MediaUpload.id == upload_id, MediaUpload.tenant_id == x_tenant_id)
        .options(selectinload(MediaUpload.frames))
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Media upload '{upload_id}' not found.",
        )

    frames_summary = [
        FrameScoreSummary(
            frame_index=f.frame_index,
            timestamp_ms=f.timestamp_ms,
            color=f.color,
            deepfake_score=f.deepfake_score,
            sensitive_score=f.sensitive_score,
            uncertainty_score=f.uncertainty_score,
        )
        for f in sorted(entry.frames, key=lambda x: x.frame_index)
    ]

    return UploadStatusResponse(
        upload_id=entry.id,
        tenant_id=entry.tenant_id,
        filename=entry.filename,
        mime_type=entry.mime_type,
        sha256_hash=entry.sha256_hash,
        status=entry.status,
        verdict=entry.verdict,
        total_frames=entry.total_frames,
        red_frames=entry.red_frame_count,
        yellow_frames=entry.yellow_frame_count,
        green_frames=entry.green_frame_count,
        frames=frames_summary,
        published_url=entry.published_key,
        created_at=entry.created_at.isoformat(),
        completed_at=entry.completed_at.isoformat() if entry.completed_at else None,
    )


@router.get(
    "/audit/verify",
    response_model=AuditVerifyResponse,
    summary="Verify HMAC-SHA256 audit ledger cryptographic integrity",
)
async def verify_audit_ledger(
    db: AsyncSession = Depends(get_db_session),
) -> AuditVerifyResponse:
    """
    Verifies the immutable audit ledger hash chain from genesis to the most recent entry.
    """
    res = await verify_ledger_integrity(session=db)
    return AuditVerifyResponse(
        is_valid=res.is_valid,
        total_records=res.total_records,
        last_sequence=res.last_sequence,
        last_signature=res.last_signature,
        verified_at=res.verified_at,
    )


@router.get(
    "/healthz",
    response_model=HealthCheckResponse,
    tags=["System"],
    summary="System health probe",
)
async def healthcheck(
    db: AsyncSession = Depends(get_db_session),
) -> HealthCheckResponse:
    """
    Readiness probe validating database connectivity and fail-closed state.
    """
    db_connected = True
    try:
        from sqlalchemy import text

        await db.execute(text("SELECT 1"))
    except Exception:
        db_connected = False

    return HealthCheckResponse(
        status="ok" if db_connected else "degraded",
        version="0.1.0",
        environment=settings.environment,
        fail_closed_mode=settings.policy.fail_closed_mode,
        database_connected=db_connected,
    )
