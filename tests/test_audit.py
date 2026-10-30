"""
SafeGate — Unit Tests for Cryptographic Audit Logging (Phase 4)
================================================================
Verifies:
1. Genesis block initialization (`previous_hash = "0" * 64`).
2. Sequential hash chaining: each row's hash incorporates the prior row's hash.
3. Successful verification of untampered chains.
4. Detection of payload modification (tampering with action, details, or timestamps).
5. Detection of row deletion / broken pointer linkage.
"""

import json
from app.db import SessionLocal
from app.models.database import AuditLog
from app.pipeline.audit import append_audit_log, verify_audit_chain, GENESIS_PREVIOUS_HASH


def test_audit_empty_log_valid():
    """Verify an empty audit table reports as valid."""
    db = SessionLocal()
    try:
        db.query(AuditLog).delete()
        db.commit()

        res = verify_audit_chain(db)
        assert res["valid"] is True
        assert res["total_entries"] == 0
        assert res["broken_at"] is None
    finally:
        db.close()


def test_audit_hash_chain_creation_and_verification():
    """
    Verify creating sequential audit entries:
    - Row 1 has genesis previous_hash (64 zeros).
    - Row 2 has previous_hash equal to Row 1's row_hash.
    - Whole chain passes verify_audit_chain().
    """
    db = SessionLocal()
    try:
        db.query(AuditLog).delete()
        db.commit()

        # 1. Append first event
        e1 = append_audit_log(
            action="upload_received",
            details={"filename": "test1.mp4", "size": 1024},
            upload_id="11111111111111111111111111111111",
            db=db,
        )
        assert e1.previous_hash == GENESIS_PREVIOUS_HASH
        assert len(e1.row_hash) == 64

        # 2. Append second event
        e2 = append_audit_log(
            action="verdict_allow",
            details={"verdict": "ALLOW", "duration": 0.5},
            upload_id=e1.upload_id,
            db=db,
        )
        assert e2.previous_hash == e1.row_hash

        # 3. Append third event
        e3 = append_audit_log(
            action="file_published",
            details={"destination": "published/test1.mp4"},
            upload_id=e1.upload_id,
            db=db,
        )
        assert e3.previous_hash == e2.row_hash

        # 4. Verify chain integrity
        check = verify_audit_chain(db)
        assert check["valid"] is True
        assert check["total_entries"] == 3
        assert check["broken_at"] is None
        assert "verified" in check["message"].lower()
    finally:
        db.query(AuditLog).delete()
        db.commit()
        db.close()


def test_audit_detects_tampered_record():
    """
    Simulate an attacker modifying a historical database record:
    - Change details from 'verdict_block' to 'verdict_allow'.
    - verify_audit_chain() must detect the mismatch and identify the exact broken row ID.
    """
    db = SessionLocal()
    try:
        db.query(AuditLog).delete()
        db.commit()

        # Insert 3 legitimate entries
        e1 = append_audit_log("upload_received", {"file": "bad.mp4"}, "22222222222222222222222222222222", db)
        e2 = append_audit_log("verdict_block", {"reason": "NSFW detected"}, "22222222222222222222222222222222", db)
        e3 = append_audit_log("file_destroyed", {"target": "quarantine"}, "22222222222222222222222222222222", db)

        # TAMPER: An attacker alters e2's details in SQLite without recomputing hash
        e2_row = db.query(AuditLog).filter(AuditLog.id == e2.id).first()
        e2_row.details = json.dumps({"reason": "TAMPERED_COVERUP"})
        db.commit()

        # Verification must fail and pinpoint e2's ID
        check = verify_audit_chain(db)
        assert check["valid"] is False
        assert check["broken_at"] == e2.id
        assert "tampered" in check["message"].lower() or "violation" in check["message"].lower()
    finally:
        db.query(AuditLog).delete()
        db.commit()
        db.close()


def test_audit_detects_deleted_record():
    """
    Simulate an attacker deleting a historical audit row:
    - The linkage between the surrounding rows will be broken.
    """
    db = SessionLocal()
    try:
        db.query(AuditLog).delete()
        db.commit()

        e1 = append_audit_log("event_1", {"v": 1}, None, db)
        e2 = append_audit_log("event_2", {"v": 2}, None, db)
        e3 = append_audit_log("event_3", {"v": 3}, None, db)

        # TAMPER: Delete intermediate row e2
        db.query(AuditLog).filter(AuditLog.id == e2.id).delete()
        db.commit()

        check = verify_audit_chain(db)
        assert check["valid"] is False
        assert check["broken_at"] == e3.id
        assert "linkage broken" in check["message"].lower()
    finally:
        db.query(AuditLog).delete()
        db.commit()
        db.close()
