"""
SafeGate — End-to-End Screening Pipeline Tests (Phase 2)
=========================================================
Tests the entire orchestrated pipeline flow (`run_pipeline`):
1. Clean video execution:
   - Evaluates all stages.
   - Reaches ALLOW verdict.
   - Relocates video safely from quarantine/ to published/.
2. Fail-closed BLOCK execution:
   - Triggers BLOCK via lowered test thresholds or blocklist match.
   - Verifies the physical video is DESTROYED immediately from disk (defensive rule).
   - Verifies SHA-256 and frame pHashes are recorded in blocklist tables.
3. Subsequent upload of blocked content:
   - Immediate Stage 2 exact hash match -> instant BLOCK without re-evaluating ML stages.
4. Broken/unreadable media:
   - Routes to REVIEW (fail-closed).
"""

import os
from pathlib import Path
import pytest
from app.config import settings
from app.db import SessionLocal
from app.models.database import Upload, BlocklistHash, BlocklistPHash
from app.pipeline.intake import save_upload, cleanup_file
from app.pipeline.orchestrator import run_pipeline


@pytest.fixture(autouse=True)
def enable_mock_model_for_speed():
    """Use fast deterministic mock classifier during unit test runs."""
    old_val = os.environ.get("SAFEGATE_MOCK_MODEL")
    os.environ["SAFEGATE_MOCK_MODEL"] = "true"
    os.environ["SAFEGATE_MOCK_NSFW_SCORE"] = "0.02"  # Clean score by default
    yield
    if old_val is not None:
        os.environ["SAFEGATE_MOCK_MODEL"] = old_val
    else:
        os.environ.pop("SAFEGATE_MOCK_MODEL", None)
    os.environ.pop("SAFEGATE_MOCK_NSFW_SCORE", None)


def test_pipeline_clean_video_allowed(generate_synthetic_video):
    """
    Upload a clean synthetic video:
    - Passes all stages.
    - Receives ALLOW verdict.
    - File is moved to published/ directory.
    """
    db = SessionLocal()
    _, video_bytes = generate_synthetic_video(duration_sec=2)

    # Stage 1: Intake
    file_path, stored_name, orig_name, file_size = save_upload(video_bytes, "clean_video.mp4")

    upload_rec = Upload(
        original_filename=orig_name,
        stored_filename=stored_name,
        file_size=file_size,
        verdict="REVIEW",
    )
    db.add(upload_rec)
    db.commit()
    db.refresh(upload_rec)

    try:
        # Run full pipeline
        result = run_pipeline(upload_rec.id, file_path, db)

        assert result.verdict == "ALLOW"
        assert "Clean" in result.explanation

        # Verify file was moved from quarantine/ to published/
        published_file = settings.published_path / stored_name
        assert published_file.exists()
        assert not file_path.exists()  # Not in quarantine anymore
    finally:
        published_file = settings.published_path / stored_name
        cleanup_file(published_file)
        db.close()


def test_pipeline_block_path_destroys_file_and_indexes_hashes(generate_synthetic_video):
    """
    Test BLOCK pathway safely:
    - Set mock NSFW score to 0.95 (exceeds BLOCK_THRESHOLD 0.85).
    - Verifies file is deleted on BLOCK.
    - Verifies SHA-256 and pHashes are recorded into blocklist.
    - Verifies subsequent re-upload is blocked at Stage 2 (exact hash).
    """
    db = SessionLocal()
    os.environ["SAFEGATE_MOCK_NSFW_SCORE"] = "0.95"  # Simulate explicit score safely

    _, video_bytes = generate_synthetic_video(duration_sec=2)

    # 1. First Upload
    file_path, stored_name, orig_name, file_size = save_upload(video_bytes, "flagged_upload.mp4")

    upload_rec1 = Upload(
        original_filename=orig_name,
        stored_filename=stored_name,
        file_size=file_size,
        verdict="REVIEW",
    )
    db.add(upload_rec1)
    db.commit()
    db.refresh(upload_rec1)

    try:
        result1 = run_pipeline(upload_rec1.id, file_path, db)

        assert result1.verdict == "BLOCK"
        assert result1.stored_filename == "DELETED_ON_BLOCK"
        # Confirm physical file was wiped from disk
        assert not file_path.exists()

        # Confirm SHA-256 is in blocklist_hashes table
        sha_record = db.query(BlocklistHash).filter(BlocklistHash.sha256_hash == result1.sha256_hash).first()
        assert sha_record is not None

        # Confirm frame pHashes were indexed
        phash_count = db.query(BlocklistPHash).count()
        assert phash_count > 0

        # 2. Re-upload identical video (Stage 2 Exact Deduplication Test)
        os.environ["SAFEGATE_MOCK_NSFW_SCORE"] = "0.02"  # Reset model score
        file_path2, stored_name2, orig_name2, file_size2 = save_upload(video_bytes, "reupload_attempt.mp4")

        upload_rec2 = Upload(
            original_filename=orig_name2,
            stored_filename=stored_name2,
            file_size=file_size2,
            verdict="REVIEW",
        )
        db.add(upload_rec2)
        db.commit()
        db.refresh(upload_rec2)

        result2 = run_pipeline(upload_rec2.id, file_path2, db)

        # Must be blocked at Stage 2 without needing frame extraction or model inference
        assert result2.verdict == "BLOCK"
        assert "Exact match" in result2.explanation
        assert not file_path2.exists()  # Deleted immediately

    finally:
        # Clean up test blocklist records
        if upload_rec1.sha256_hash:
            db.query(BlocklistHash).filter(BlocklistHash.sha256_hash == upload_rec1.sha256_hash).delete()
        db.query(BlocklistPHash).delete()
        db.commit()
        db.close()


def test_pipeline_failclosed_on_corrupted_file():
    """
    Verify that if video processing throws an error mid-pipeline,
    the fail-closed policy routes the upload to REVIEW and moves it to review/.
    """
    db = SessionLocal()
    # Write garbage into quarantine
    quarantine_dir = settings.quarantine_path
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    corrupted_path = quarantine_dir / "corrupted_test.mp4"
    corrupted_path.write_bytes(b"ftypmp42" + b"\x00" * 500)  # Has valid start bytes but corrupt stream

    upload_rec = Upload(
        original_filename="corrupted.mp4",
        stored_filename=corrupted_path.name,
        file_size=len(corrupted_path.read_bytes()),
        verdict="REVIEW",
    )
    db.add(upload_rec)
    db.commit()
    db.refresh(upload_rec)

    try:
        result = run_pipeline(upload_rec.id, corrupted_path, db)
        assert result.verdict == "REVIEW"
        assert "Fail-closed" in result.explanation

        # Verify file was safely moved to review/
        review_file = settings.review_path / corrupted_path.name
        assert review_file.exists()
    finally:
        review_file = settings.review_path / corrupted_path.name
        cleanup_file(review_file)
        cleanup_file(corrupted_path)
        db.close()
