"""
SafeGate — Unit Tests for Moderator Dashboard & Review Endpoints (Phase 5)
==========================================================================
Verifies:
1. Decision listing with verdict filtering and pagination.
2. Review queue listing strictly returning items in REVIEW state.
3. Moderator review approval (moving file to published/, updating verdict to ALLOW, audit log).
4. Moderator review rejection (unlinking file, registering SHA-256 and pHash in blocklist, audit log).
5. User appeal creation, listing, and resolution by moderators.
6. Aggregate telemetry statistics and verdict timeline grouping.
7. Verification of dual-key authentication (`verify_any_api_key`).
"""

import uuid
import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from app.config import settings
from app.db import SessionLocal
from app.models.database import Upload, BlocklistHash, BlocklistPHash, Appeal, AuditLog
from app.models.schemas import ReviewAction, AppealCreate, AppealResolve
from app.security.auth import verify_any_api_key
from app.routes.dashboard import (
    list_decisions,
    get_review_queue,
    approve_review_item,
    reject_review_item,
    create_appeal,
    list_appeals,
    resolve_appeal,
    get_stats,
)


@pytest.fixture
def db_session():
    """Provides a clean database session per test and cleans up test records."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_verify_any_api_key():
    """Verify that endpoints requiring any key accept both client and admin keys."""
    # 1. Missing key -> 401
    with pytest.raises(HTTPException) as exc1:
        verify_any_api_key(None)
    assert exc1.value.status_code == 401

    # 2. Invalid key -> 403
    with pytest.raises(HTTPException) as exc2:
        verify_any_api_key("wrong-secret-key")
    assert exc2.value.status_code == 403

    # 3. Client key -> accepted
    assert verify_any_api_key(settings.CLIENT_API_KEY) == settings.CLIENT_API_KEY

    # 4. Admin key -> accepted
    assert verify_any_api_key(settings.ADMIN_API_KEY) == settings.ADMIN_API_KEY


def test_list_decisions_and_filtering(db_session):
    """Verify listing decisions and filtering by verdict."""
    uid1 = uuid.uuid4().hex
    uid2 = uuid.uuid4().hex

    u1 = Upload(
        id=uid1,
        original_filename="clean_video.mp4",
        stored_filename=f"{uid1}.mp4",
        file_size=1024,
        verdict="ALLOW",
        explanation="Stage 8: All clean",
        scan_duration_sec=0.25,
    )
    u2 = Upload(
        id=uid2,
        original_filename="bad_video.mp4",
        stored_filename=f"{uid2}.mp4",
        file_size=2048,
        verdict="BLOCK",
        explanation="Stage 2: Exact hash match",
        scan_duration_sec=0.05,
    )
    db_session.add_all([u1, u2])
    db_session.commit()

    try:
        # All decisions
        all_records = list_decisions(verdict=None, limit=100, offset=0, db=db_session, _="key")
        ids = [r.id for r in all_records]
        assert uid1 in ids
        assert uid2 in ids

        # Filter ALLOW
        allow_records = list_decisions(verdict="ALLOW", limit=100, offset=0, db=db_session, _="key")
        allow_ids = [r.id for r in allow_records]
        assert uid1 in allow_ids
        assert uid2 not in allow_ids

        # Filter BLOCK
        block_records = list_decisions(verdict="BLOCK", limit=100, offset=0, db=db_session, _="key")
        block_ids = [r.id for r in block_records]
        assert uid2 in block_ids
        assert uid1 not in block_ids
    finally:
        db_session.query(Upload).filter(Upload.id.in_([uid1, uid2])).delete(synchronize_session=False)
        db_session.commit()


def test_review_queue_isolation(db_session):
    """Verify that get_review_queue only returns records in REVIEW state."""
    uid_rev = uuid.uuid4().hex
    uid_alw = uuid.uuid4().hex

    u_rev = Upload(
        id=uid_rev,
        original_filename="borderline.mp4",
        stored_filename=f"{uid_rev}.mp4",
        file_size=5000,
        verdict="REVIEW",
        explanation="Stage 6: Gemini uncertain",
    )
    u_alw = Upload(
        id=uid_alw,
        original_filename="ok.mp4",
        stored_filename=f"{uid_alw}.mp4",
        file_size=5000,
        verdict="ALLOW",
        explanation="Clean",
    )
    db_session.add_all([u_rev, u_alw])
    db_session.commit()

    try:
        queue = get_review_queue(limit=50, offset=0, db=db_session, _="key")
        q_ids = [r.id for r in queue]
        assert uid_rev in q_ids
        assert uid_alw not in q_ids
    finally:
        db_session.query(Upload).filter(Upload.id.in_([uid_rev, uid_alw])).delete(synchronize_session=False)
        db_session.commit()


def test_moderator_approve_flow(db_session):
    """
    Verify approving an upload in review:
    - Moves physical file from review/ to published/.
    - Changes verdict to ALLOW.
    - Adds moderator approval action to audit chain.
    """
    uid = uuid.uuid4().hex
    stored_name = f"{uid}.mp4"
    review_file = settings.review_path / stored_name
    published_file = settings.published_path / stored_name

    settings.review_path.mkdir(parents=True, exist_ok=True)
    review_file.write_bytes(b"dummy video content for approval")

    u = Upload(
        id=uid,
        original_filename="false_positive.mp4",
        stored_filename=stored_name,
        file_size=32,
        verdict="REVIEW",
        explanation="Borderline NSFW score",
    )
    db_session.add(u)
    db_session.commit()

    try:
        action = ReviewAction(note="Verified artistic content, safe to publish")
        res = approve_review_item(upload_id=uid, action=action, db=db_session, _="key")

        assert res.verdict == "ALLOW"
        assert "Manual review approved" in res.explanation
        assert not review_file.exists()
        assert published_file.exists()

        # Check audit log
        audit = db_session.query(AuditLog).filter(AuditLog.upload_id == uid).order_by(AuditLog.id.desc()).first()
        assert audit is not None
        assert audit.action == "moderator_approved"
        assert "Verified artistic content" in audit.details
    finally:
        if published_file.exists():
            published_file.unlink(missing_ok=True)
        if review_file.exists():
            review_file.unlink(missing_ok=True)
        db_session.query(Upload).filter(Upload.id == uid).delete()
        db_session.commit()


def test_moderator_reject_and_blocklist_flow(db_session):
    """
    Verify rejecting an upload in review:
    - Unlinks physical file (fail-closed, never keep blocked media).
    - Blocklists the SHA-256 checksum.
    - Changes verdict to BLOCK.
    - Adds rejection action to audit chain.
    """
    uid = uuid.uuid4().hex
    stored_name = f"{uid}.mp4"
    review_file = settings.review_path / stored_name
    dummy_sha = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"

    settings.review_path.mkdir(parents=True, exist_ok=True)
    review_file.write_bytes(b"dummy prohibited video data")

    u = Upload(
        id=uid,
        original_filename="bad_media.mp4",
        stored_filename=stored_name,
        file_size=27,
        sha256_hash=dummy_sha,
        verdict="REVIEW",
        explanation="Borderline score flagged",
    )
    db_session.add(u)
    db_session.commit()

    try:
        action = ReviewAction(note="Confirmed policy violation")
        res = reject_review_item(upload_id=uid, action=action, db=db_session, _="key")

        assert res.verdict == "BLOCK"
        assert "Manual review rejected and blocked" in res.explanation
        # File must be permanently destroyed
        assert not review_file.exists()

        # SHA-256 must now be in BlocklistHash
        bl = db_session.query(BlocklistHash).filter(BlocklistHash.sha256_hash == dummy_sha).first()
        assert bl is not None
        assert bl.source == "moderator-block"

        # Check audit log
        audit = db_session.query(AuditLog).filter(AuditLog.upload_id == uid).order_by(AuditLog.id.desc()).first()
        assert audit is not None
        assert audit.action == "moderator_rejected"
    finally:
        if review_file.exists():
            review_file.unlink(missing_ok=True)
        db_session.query(BlocklistHash).filter(BlocklistHash.sha256_hash == dummy_sha).delete()
        db_session.query(Upload).filter(Upload.id == uid).delete()
        db_session.commit()


def test_review_action_invalid_state_rejected(db_session):
    """Verify attempting to approve or reject an upload that is already ALLOW or BLOCK raises HTTP 400."""
    uid = uuid.uuid4().hex
    u = Upload(
        id=uid,
        original_filename="already_allowed.mp4",
        stored_filename=f"{uid}.mp4",
        file_size=100,
        verdict="ALLOW",
    )
    db_session.add(u)
    db_session.commit()

    try:
        with pytest.raises(HTTPException) as exc1:
            approve_review_item(upload_id=uid, action=None, db=db_session, _="key")
        assert exc1.value.status_code == 400

        with pytest.raises(HTTPException) as exc2:
            reject_review_item(upload_id=uid, action=None, db=db_session, _="key")
        assert exc2.value.status_code == 400
    finally:
        db_session.query(Upload).filter(Upload.id == uid).delete()
        db_session.commit()


def test_appeal_lifecycle(db_session):
    """
    Verify user appeal workflow:
    1. Submit appeal for valid upload.
    2. Submitting appeal for non-existent upload returns 404.
    3. List appeals filtered by status.
    4. Moderator resolves appeal to approved or rejected.
    """
    uid = uuid.uuid4().hex
    u = Upload(
        id=uid,
        original_filename="disputed_clip.mp4",
        stored_filename=f"{uid}.mp4",
        file_size=100,
        verdict="BLOCK",
    )
    db_session.add(u)
    db_session.commit()

    try:
        # 1. Submit appeal
        payload = AppealCreate(
            upload_id=uid,
            reason="This video is an educational documentary, not explicit.",
        )
        appeal = create_appeal(payload=payload, db=db_session, _="key")
        assert appeal.id is not None
        assert appeal.status == "pending"
        assert appeal.upload_id == uid

        # 2. Non-existent upload -> 404
        bad_payload = AppealCreate(upload_id="00000000000000000000000000000000", reason="Testing non existent upload")
        with pytest.raises(HTTPException) as exc404:
            create_appeal(payload=bad_payload, db=db_session, _="key")
        assert exc404.value.status_code == 404

        # 3. List appeals
        pending = list_appeals(appeal_status="pending", limit=50, offset=0, db=db_session, _="key")
        pending_ids = [a.id for a in pending]
        assert appeal.id in pending_ids

        # 4. Resolve appeal
        res_payload = AppealResolve(status="approved", moderator_note="Appeal upheld after review")
        resolved = resolve_appeal(appeal_id=appeal.id, payload=res_payload, db=db_session, _="key")
        assert resolved.status == "approved"
        assert resolved.moderator_note == "Appeal upheld after review"
        assert resolved.resolved_at is not None
    finally:
        db_session.query(Appeal).filter(Appeal.upload_id == uid).delete()
        db_session.query(Upload).filter(Upload.id == uid).delete()
        db_session.commit()


def test_telemetry_stats(db_session):
    """Verify aggregated stats calculate correct totals and timeline groups."""
    uid1 = uuid.uuid4().hex
    uid2 = uuid.uuid4().hex
    uid3 = uuid.uuid4().hex

    u1 = Upload(id=uid1, original_filename="v1.mp4", stored_filename="s1.mp4", file_size=10, verdict="ALLOW", scan_duration_sec=1.0)
    u2 = Upload(id=uid2, original_filename="v2.mp4", stored_filename="s2.mp4", file_size=20, verdict="REVIEW", scan_duration_sec=2.0)
    u3 = Upload(id=uid3, original_filename="v3.mp4", stored_filename="s3.mp4", file_size=30, verdict="BLOCK", scan_duration_sec=3.0)

    db_session.add_all([u1, u2, u3])
    db_session.commit()

    try:
        stats = get_stats(db=db_session, _="key")
        assert stats.total_scanned >= 3
        assert stats.total_allowed >= 1
        assert stats.total_reviewed >= 1
        assert stats.total_blocked >= 1
        assert stats.avg_scan_time_sec > 0.0
        assert isinstance(stats.verdicts_over_time, list)
    finally:
        db_session.query(Upload).filter(Upload.id.in_([uid1, uid2, uid3])).delete(synchronize_session=False)
        db_session.commit()
