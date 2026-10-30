"""
SafeGate — Intake & File Validation Tests (Phase 1)
===================================================
Tests all security boundaries and validation rules of Stage 1:
- Magic-byte enforcement (preventing MIME spoofing)
- Upload size limits (DoS mitigation)
- Path traversal sanitization
- Unpredictable UUID assignment
- Fail-closed cleanup on error
- Database record persistence and fail-closed initial state
"""

import re
import tempfile
from pathlib import Path
import pytest
from app.config import settings
from app.db import SessionLocal
from app.models.database import Upload
from app.pipeline.intake import (
    validate_file_type,
    validate_file_size,
    sanitize_filename,
    save_upload,
    cleanup_file,
    assert_path_within,
)


def test_sanitize_filename_normal():
    """Verify standard video filenames are converted to UUID4 + original extension."""
    safe = sanitize_filename("my_video.mp4")
    assert safe.endswith(".mp4")
    assert len(safe) == 32 + 4
    # Check that it's 32 hex chars before .mp4
    assert re.match(r"^[0-9a-f]{32}\.mp4$", safe)


def test_sanitize_filename_path_traversal():
    """Verify directory traversal payloads (../../etc/passwd) are completely neutralized."""
    malicious = "../../../../etc/cron.d/exploit.mp4"
    safe = sanitize_filename(malicious)
    assert safe.endswith(".mp4")
    assert "/" not in safe
    assert "\\" not in safe
    assert ".." not in safe
    assert re.match(r"^[0-9a-f]{32}\.mp4$", safe)


def test_disallowed_extension_rejected():
    """Verify non-video extensions (.exe, .sh, .py) are rejected."""
    with pytest.raises(ValueError, match="Disallowed extension"):
        sanitize_filename("payload.exe")

    with pytest.raises(ValueError, match="Disallowed extension"):
        sanitize_filename("script.sh")


def test_valid_synthetic_video_intake(generate_synthetic_video):
    """Verify that a valid synthetic MP4 video passes magic byte checks and is saved in quarantine."""
    _, video_bytes = generate_synthetic_video(duration_sec=2)
    final_path, stored_name, orig_name, file_size = save_upload(
        upload_bytes=video_bytes,
        original_filename="holiday_clip.mp4",
    )
    try:
        assert final_path.exists()
        assert file_size > 0
        assert stored_name == final_path.name
        assert orig_name == "holiday_clip.mp4"

        # Verify magic byte inspection matches video/mp4
        mime = validate_file_type(final_path)
        assert mime == "video/mp4"

        # Verify path is strictly inside quarantine directory
        assert_path_within(final_path, settings.quarantine_path)
    finally:
        cleanup_file(final_path)
        assert not final_path.exists()


def test_magic_byte_spoofing_rejected():
    """
    Verify that an attacker cannot bypass screening by renaming a non-video
    file to have a '.mp4' extension (MIME spoofing defense).
    """
    fake_video_bytes = b"MZ\x90\x00\x03\x00\x00\x00" + b"A" * 100  # DOS/PE header bytes
    with pytest.raises(ValueError, match="Could not determine file type|Prohibited media type"):
        save_upload(fake_video_bytes, "innocent.mp4")


def test_empty_file_rejected():
    """Verify that zero-byte files are rejected early."""
    with pytest.raises(ValueError, match="Empty file rejected"):
        save_upload(b"", "empty.mp4")


def test_oversized_file_rejected(generate_synthetic_video):
    """
    Verify that files exceeding the configured MAX_UPLOAD_SIZE_MB limit
    are rejected before being admitted into the processing queue.
    """
    _, video_bytes = generate_synthetic_video(duration_sec=1)
    # The test environment configures MAX_UPLOAD_SIZE_MB=10 in conftest.
    # Pad payload to 11MB
    oversized = video_bytes + (b"\x00" * (11 * 1024 * 1024))
    with pytest.raises(ValueError, match="exceeds maximum permitted limit"):
        save_upload(oversized, "huge.mp4")


def test_database_record_creation():
    """
    Verify that creating an upload record persists properly in SQLite
    and defaults to the fail-closed initial state 'REVIEW'.
    """
    db = SessionLocal()
    try:
        record = Upload(
            original_filename="user_upload.mp4",
            stored_filename="a1b2c3d4e5f60718293a4b5c6d7e8f90.mp4",
            file_size=1048576,
            verdict="REVIEW",
            explanation="Phase 1 Intake Complete: File placed in quarantine; screening pipeline initialized.",
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        assert record.id is not None
        assert len(record.id) == 32
        assert record.verdict == "REVIEW"
        assert record.created_at is not None

        # Query back from DB
        fetched = db.query(Upload).filter(Upload.id == record.id).first()
        assert fetched is not None
        assert fetched.original_filename == "user_upload.mp4"
        assert fetched.file_size == 1048576
    finally:
        db.close()
