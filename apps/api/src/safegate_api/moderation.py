"""
SafeGate Moderation Console Subsystem.
Implements the human review queue, forensic evidence packages, and cryptographically audited actions.
Enforces moderator wellness: visual obfuscation and blurred thumbnails by default.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from safegate_api.audit import record_audit_event
from safegate_api.database import get_db_session
from safegate_api.logging import logger
from safegate_api.models import MediaUpload
from safegate_api.routes import storage_client
from safegate_api.schemas import FrameScoreSummary

router = APIRouter(prefix="/v1/moderation", tags=["Moderation Console"])


class ReviewQueueItem(BaseModel):
    upload_id: str
    tenant_id: str
    filename: str
    created_at: str
    yellow_frame_count: int
    total_frames: int
    status: str


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]
    total_count: int
    offset: int
    limit: int


class ReviewPackageResponse(BaseModel):
    upload_id: str
    tenant_id: str
    filename: str
    file_size_bytes: int
    mime_type: str
    sha256_hash: str
    verdict: str
    total_frames: int
    red_frames: int
    yellow_frames: int
    green_frames: int
    blur_default: bool = Field(
        default=True,
        description="Trust & Safety wellness: sensitive frames blurred by default.",
    )
    frames: list[FrameScoreSummary]


class ReviewerActionRequest(BaseModel):
    action: str = Field(
        description="Moderation outcome: 'APPROVE' (clear to publish) or 'REJECT' (confirm block)"
    )
    reviewer_id: str = Field(description="Authenticated reviewer identity")
    notes: str = Field(description="Auditable justification for the moderation action")
    category: str | None = Field(
        default=None, description="Specific category: False Positive, Parody, Graphic, etc."
    )


class ReviewerActionResponse(BaseModel):
    upload_id: str
    final_verdict: str  # ALLOW or BLOCK
    reviewer_id: str
    timestamp: str
    audit_sequence: int
    message: str


@router.get(
    "/queue",
    response_model=ReviewQueueResponse,
    summary="List media assets pending human moderation",
)
async def list_moderation_queue(
    tenant_id: str | None = Query(default=None, description="Filter by tenant ID"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> ReviewQueueResponse:
    """
    Retrieves prioritized list of uploads in HUMAN_REVIEW status.
    """
    query = select(MediaUpload).where(MediaUpload.verdict == "HUMAN_REVIEW")
    count_query = select(func.count(MediaUpload.id)).where(MediaUpload.verdict == "HUMAN_REVIEW")

    if tenant_id:
        query = query.where(MediaUpload.tenant_id == tenant_id)
        count_query = count_query.where(MediaUpload.tenant_id == tenant_id)

    query = query.order_by(MediaUpload.created_at.asc()).offset(offset).limit(limit)

    total_count_res = await db.execute(count_query)
    total_count = total_count_res.scalar() or 0

    res = await db.execute(query)
    entries = res.scalars().all()

    items = [
        ReviewQueueItem(
            upload_id=e.id,
            tenant_id=e.tenant_id,
            filename=e.filename,
            created_at=e.created_at.isoformat(),
            yellow_frame_count=e.yellow_frame_count,
            total_frames=e.total_frames,
            status=e.status,
        )
        for e in entries
    ]

    return ReviewQueueResponse(
        items=items,
        total_count=total_count,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{upload_id}",
    response_model=ReviewPackageResponse,
    summary="Get full forensic package for human review",
)
async def get_review_package(
    upload_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ReviewPackageResponse:
    """
    Retrieves all extracted frame scores, uncertainty metrics, and forensic cues with wellness blurring.
    """
    stmt = (
        select(MediaUpload)
        .where(MediaUpload.id == upload_id)
        .options(selectinload(MediaUpload.frames))
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload '{upload_id}' not found.",
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

    return ReviewPackageResponse(
        upload_id=entry.id,
        tenant_id=entry.tenant_id,
        filename=entry.filename,
        file_size_bytes=entry.file_size_bytes,
        mime_type=entry.mime_type,
        sha256_hash=entry.sha256_hash,
        verdict=entry.verdict,
        total_frames=entry.total_frames,
        red_frames=entry.red_frame_count,
        yellow_frames=entry.yellow_frame_count,
        green_frames=entry.green_frame_count,
        blur_default=True,
        frames=frames_summary,
    )


@router.post(
    "/{upload_id}/action",
    response_model=ReviewerActionResponse,
    summary="Submit human moderator verdict (APPROVE or REJECT)",
)
async def submit_reviewer_action(
    upload_id: str,
    body: ReviewerActionRequest,
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-ID")] = "default-tenant",
    db: AsyncSession = Depends(get_db_session),
) -> ReviewerActionResponse:
    """
    Applies human moderation decision.
    If APPROVE: promotes quarantined asset to published storage and issues ALLOW.
    If REJECT: locks asset in BLOCK.
    Both decisions are permanently recorded in the HMAC-SHA256 audit ledger.
    """
    action_upper = body.action.strip().upper()
    if action_upper not in {"APPROVE", "REJECT"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be either 'APPROVE' or 'REJECT'.",
        )

    stmt = select(MediaUpload).where(
        MediaUpload.id == upload_id,
        MediaUpload.tenant_id == x_tenant_id,
    )
    res = await db.execute(stmt)
    entry = res.scalar_one_or_none()

    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload '{upload_id}' not found.",
        )

    now = datetime.now(UTC)
    final_verdict = "ALLOW" if action_upper == "APPROVE" else "BLOCK"
    entry.verdict = final_verdict
    entry.completed_at = now

    # If approved, promote from quarantine to published bucket
    if final_verdict == "ALLOW":
        try:
            pub_key = storage_client.promote_to_published(
                key=entry.quarantine_key,
                allow_confirmed=True,
            )
            entry.published_key = pub_key
        except Exception as stor_err:
            logger.error(f"Failed to promote approved asset {upload_id}: {stor_err}")

    # Append to HMAC-SHA256 audit ledger
    audit_entry = await record_audit_event(
        session=db,
        event_type="HUMAN_REVIEW_DECISION",
        tenant_id=entry.tenant_id,
        upload_id=upload_id,
        payload={
            "action": action_upper,
            "final_verdict": final_verdict,
            "reviewer_id": body.reviewer_id,
            "notes": body.notes,
            "category": body.category,
        },
    )

    await db.commit()
    logger.info(
        f"Reviewer '{body.reviewer_id}' submitted action '{action_upper}' for upload '{upload_id}' -> {final_verdict}"
    )

    return ReviewerActionResponse(
        upload_id=upload_id,
        final_verdict=final_verdict,
        reviewer_id=body.reviewer_id,
        timestamp=now.isoformat(),
        audit_sequence=audit_entry.sequence_num,
        message=f"Upload successfully updated to verdict {final_verdict} by reviewer.",
    )
