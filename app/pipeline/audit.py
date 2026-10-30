"""
SafeGate — Tamper-Evident Cryptographic Audit Logging
======================================================
Implements a tamper-evident sequential audit log using cryptographic hash chaining:

HASH CHAIN ALGORITHM:
1. Genesis Row: The very first audit log record uses an initial previous_hash:
   `"0" * 64` (64 zeros).
2. Chained Rows: Every subsequent audit row computes:
   `row_hash = SHA256(previous_hash + action + details + str(upload_id) + created_at)`
3. Tamper Detection (`verify_audit_chain`):
   Traverses the entire table sequentially:
   - Verifies that row[i].previous_hash == row[i-1].row_hash.
   - Recalculates the SHA-256 for each row's contents.
   - If any past record was modified, injected, or deleted, the mathematical link
     breaks at that exact row ID, and verification immediately returns `valid=False`.

VIVA EXPLANATION:
Why is this "tamper-evident" rather than "tamper-proof"?
A malicious administrator with direct SQLite write access could recompute the entire
hash chain from the point of modification forward. However, it completely prevents
casual tampering, accidental record deletion, or unauthorized in-place SQL updates.
In an enterprise environment, the tip hash of this chain can be anchored to an external
time-stamping authority or immutable transparency log.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.database import AuditLog

logger = logging.getLogger(__name__)

GENESIS_PREVIOUS_HASH = "0" * 64


def _compute_row_hash(
    previous_hash: str,
    action: str,
    details: str,
    upload_id: Optional[str],
    created_at_str: str,
) -> str:
    """
    Computes deterministic SHA-256 hash chaining the previous block hash with current row data.
    Uses standard '%Y-%m-%d %H:%M:%S' formatting to ensure consistency across SQLite storage.
    """
    payload = f"{previous_hash}|{action}|{details}|{upload_id or ''}|{created_at_str}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def append_audit_log(
    action: str,
    details: Dict[str, Any],
    upload_id: Optional[str],
    db: Session,
) -> AuditLog:
    """
    Appends a new event record to the tamper-evident audit log.

    Args:
        action: Event identifier (e.g. 'upload_received', 'verdict_block', 'file_published').
        details: Dictionary of event-specific metadata.
        upload_id: Optional UUID of the associated upload.
        db: SQLAlchemy database session.

    Returns:
        Persisted AuditLog database model instance.
    """
    # 1. Retrieve the latest existing audit record to fetch its hash
    latest_record = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    previous_hash = latest_record.row_hash if latest_record else GENESIS_PREVIOUS_HASH

    # 2. Canonical serialization of details dictionary
    details_json = json.dumps(details, sort_keys=True)
    now_utc = datetime.now(timezone.utc)
    created_at_str = now_utc.strftime("%Y-%m-%d %H:%M:%S")

    # 3. Compute the cryptographic hash chain link
    row_hash = _compute_row_hash(
        previous_hash=previous_hash,
        action=action,
        details=details_json,
        upload_id=upload_id,
        created_at_str=created_at_str,
    )

    # 4. Create and persist record
    log_entry = AuditLog(
        action=action,
        details=details_json,
        upload_id=upload_id,
        row_hash=row_hash,
        previous_hash=previous_hash,
        created_at=now_utc,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    logger.info(
        "Audit Log #%d: [%s] row_hash=%s... prev_hash=%s...",
        log_entry.id, action, row_hash[:10], previous_hash[:10]
    )
    return log_entry


def verify_audit_chain(db: Session) -> Dict[str, Any]:
    """
    Validates the mathematical integrity of the entire audit log hash chain.

    Returns:
        Dictionary:
            - valid (bool): True if the chain is intact.
            - total_entries (int): Number of rows inspected.
            - broken_at (Optional[int]): ID of the first tampered row, or None.
            - message (str): Human-readable summary.
    """
    records = db.query(AuditLog).order_by(AuditLog.id.asc()).all()

    if not records:
        return {
            "valid": True,
            "total_entries": 0,
            "broken_at": None,
            "message": "Audit log is empty; chain is intact.",
        }

    expected_prev_hash = GENESIS_PREVIOUS_HASH

    for idx, row in enumerate(records):
        # 1. Verify previous_hash linkage
        if row.previous_hash != expected_prev_hash:
            logger.error(
                "Audit chain broken at Row #%d: expected previous_hash=%s, found=%s",
                row.id, expected_prev_hash, row.previous_hash
            )
            return {
                "valid": False,
                "total_entries": len(records),
                "broken_at": row.id,
                "message": f"Cryptographic chain linkage broken at entry ID {row.id}: previous_hash mismatch.",
            }

        # 2. Recompute row_hash over record attributes using the same '%Y-%m-%d %H:%M:%S' formatting
        created_at_str = (
            row.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(row.created_at, "strftime")
            else str(row.created_at)[:19]
        )
        recalculated_hash = _compute_row_hash(
            previous_hash=row.previous_hash,
            action=row.action,
            details=row.details,
            upload_id=row.upload_id,
            created_at_str=created_at_str,
        )

        if row.row_hash != recalculated_hash:
            logger.error(
                "Audit record payload tampered at Row #%d: recorded row_hash=%s, recalculated=%s",
                row.id, row.row_hash, recalculated_hash
            )
            return {
                "valid": False,
                "total_entries": len(records),
                "broken_at": row.id,
                "message": f"Data integrity violation at entry ID {row.id}: payload content has been modified.",
            }

        # Advance expectation pointer for next row
        expected_prev_hash = row.row_hash

    return {
        "valid": True,
        "total_entries": len(records),
        "broken_at": None,
        "message": f"Audit chain verified: all {len(records)} entries are cryptographically intact.",
    }
