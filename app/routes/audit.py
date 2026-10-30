"""
SafeGate — Audit Log Routes
=============================
Exposes endpoints for verifying and inspecting the tamper-evident audit log.
Protected by ADMIN_API_KEY.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.security.auth import verify_admin_api_key
from app.models.schemas import AuditVerifyResponse
from app.models.database import AuditLog
from app.pipeline.audit import verify_audit_chain

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get(
    "/verify",
    response_model=AuditVerifyResponse,
    summary="Verify cryptographic audit log integrity",
    description="Traverses the sequential hash chain to detect any record tampering, modification, or deletion.",
)
async def check_audit_integrity(
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_api_key),
):
    """
    Checks the entire cryptographic hash chain of the audit log.
    """
    result = verify_audit_chain(db)
    return AuditVerifyResponse(
        valid=result["valid"],
        total_entries=result["total_entries"],
        broken_at=result["broken_at"],
        message=result["message"],
    )


@router.get(
    "/logs",
    summary="List recent audit log entries",
    description="Retrieves the most recent audit log entries with their cryptographic hashes.",
)
async def list_audit_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    _admin: str = Depends(verify_admin_api_key),
) -> List[Dict[str, Any]]:
    """
    Returns the latest audit log records for the dashboard.
    """
    records = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "action": r.action,
            "details": r.details,
            "upload_id": r.upload_id,
            "row_hash": r.row_hash,
            "previous_hash": r.previous_hash,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
