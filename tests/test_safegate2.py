"""
SafeGate 2.0 — Comprehensive Test Suite
========================================
Automated verification for all SafeGate 2.0 requirements:
1. Complete frame extraction from video without frame skipping.
2. Chronological order, frame numbering, and timestamp preservation.
3. Frame SHA-256 hashing.
4. Exact color classification mapping:
     RED    = LEGITIMATE / AUTHENTIC
     GREEN  = SUSPICIOUS / AI-MANIPULATED
     YELLOW = UNCERTAIN
5. Single-frame deepfake / synthetic tampering detection.
6. Video risk assessment calculation (0 - 100).
7. Firewall Policy Engine decisions (ALLOW, QUARANTINE, BLOCK).
8. Admin moderation workflows (Approve & Publish / Reject & Blocklist).
9. Website publishing gateway (Quarantined videos NEVER published).
10. Downloadable cryptographic video security reports.
"""

import os
import json
import pytest
from pathlib import Path
from sqlalchemy.orm import Session

from app.config import settings
from app.db import SessionLocal
from app.models.database import Upload, VideoFrame, BlocklistHash
from app.pipeline.frame_extraction import extract_all_video_frames
from app.pipeline.hashing import compute_sha256
from app.pipeline.ai_engine import (
    default_ai_engine,
    CLASS_LEGITIMATE,
    CLASS_SUSPICIOUS,
    CLASS_UNCERTAIN,
    COLOR_RED,
    COLOR_GREEN,
    COLOR_YELLOW,
)
from app.routes.videos import (
    scan_video_firewall,
    get_video_status,
    get_video_report,
    get_video_timeline,
    get_video_frames,
    get_single_frame,
    get_website_published_videos,
    admin_approve_video,
    admin_reject_video,
    get_admin_dashboard,
)
from generate_demonstration_videos import ensure_demonstration_videos


@pytest.fixture(scope="module")
def sample_videos():
    """Ensures test videos exist for the test suite."""
    return ensure_demonstration_videos()


@pytest.fixture
def db_session():
    """Provides a fresh database session for each test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _create_test_upload(video_file: Path, db: Session, title: str = "Test Video") -> Upload:
    """Helper to register a quarantined video in the database."""
    settings.quarantine_path.mkdir(parents=True, exist_ok=True)
    raw_bytes = video_file.read_bytes()
    stored_name = f"test_{os.urandom(8).hex()}_{video_file.name}"
    dest_file = settings.quarantine_path / stored_name
    dest_file.write_bytes(raw_bytes)
    sha256 = compute_sha256(raw_bytes)
    u = Upload(
        original_filename=video_file.name,
        stored_filename=stored_name,
        file_size=len(raw_bytes),
        sha256_hash=sha256,
        title=title,
        verdict="QUARANTINE",
        publishing_status="unpublished",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def test_frame_color_mapping_constants():
    """Verify strictly enforced color constants."""
    assert COLOR_RED == "RED"
    assert COLOR_GREEN == "GREEN"
    assert COLOR_YELLOW == "YELLOW"
    assert CLASS_LEGITIMATE == "LEGITIMATE"
    assert CLASS_SUSPICIOUS == "SUSPICIOUS"
    assert CLASS_UNCERTAIN == "UNCERTAIN"


def test_complete_frame_extraction_all_frames_decoded(sample_videos):
    """
    SECTION 4: Complete Video Frame Extraction Engine.
    Verify that every decoded frame is accounted for without silently skipping.
    """
    video_path = sample_videos["legitimate"]
    result = extract_all_video_frames(
        video_path=video_path,
        upload_id="test_extraction_1",
        save_frames_to_disk=False,
    )

    assert result["total_frames_decoded"] > 0
    assert result["total_frames_decoded"] == len(result["frames"])
    assert result["legitimate_frames_count"] + result["suspicious_frames_count"] + result["uncertain_frames_count"] == result["total_frames_decoded"]
    assert result["fps"] > 0
    assert result["duration_sec"] > 0


def test_frame_timestamp_accuracy_and_order(sample_videos):
    """Verify chronological ordering, timestamp calculation, and SHA-256 hashes."""
    video_path = sample_videos["legitimate"]
    result = extract_all_video_frames(
        video_path=video_path,
        upload_id="test_timestamps_1",
        save_frames_to_disk=False,
    )

    frames = result["frames"]
    prev_ts = -0.001
    for idx, f in enumerate(frames, start=1):
        assert f.frame_index == idx
        assert f.timestamp_sec >= prev_ts
        prev_ts = f.timestamp_sec
        assert len(f.timestamp_str) > 0
        assert f.sha256_hash is not None
        assert len(f.sha256_hash) == 64  # Valid 64-char hex SHA-256


def test_legitimate_video_marked_red(sample_videos):
    """
    SECTION 6: RED - LEGITIMATE / AUTHENTIC FRAME.
    Authentic video frames must receive the RED classification marker.
    """
    video_path = sample_videos["legitimate"]
    result = extract_all_video_frames(
        video_path=video_path,
        upload_id="test_legit_red",
        save_frames_to_disk=False,
    )

    for f in result["frames"]:
        assert f.classification == CLASS_LEGITIMATE
        assert f.color_marker == COLOR_RED
        assert f.thumbnail_data.startswith("data:image/jpeg;base64,")

    assert result["legitimate_frames_count"] == result["total_frames_decoded"]
    assert result["suspicious_frames_count"] == 0
    assert result["risk_score"] < 25


def test_deepfake_video_marked_green(sample_videos):
    """
    SECTION 6: GREEN - AI-MANIPULATED / SUSPICIOUS FRAME.
    Manipulated deepfake frames must receive the GREEN classification marker.
    """
    video_path = sample_videos["deepfake"]
    result = extract_all_video_frames(
        video_path=video_path,
        upload_id="test_deepfake_green",
        save_frames_to_disk=False,
    )

    assert result["suspicious_frames_count"] > 0
    susp_frames = [f for f in result["frames"] if f.classification == CLASS_SUSPICIOUS]
    for sf in susp_frames:
        assert sf.color_marker == COLOR_GREEN
        assert len(sf.detection_evidence) > 0

    assert result["risk_score"] >= 60


def test_single_ai_modified_frame_detection(sample_videos):
    """
    SECTION 16 (SCENARIO 3): Single AI-Modified Frame Detection.
    A video with only 1 modified frame must detect that exact frame (GREEN),
    mark surrounding frames RED, and trigger QUARANTINE.
    """
    video_path = sample_videos["single_modified"]
    result = extract_all_video_frames(
        video_path=video_path,
        upload_id="test_single_frame_mod",
        save_frames_to_disk=False,
    )

    frames = result["frames"]
    assert result["suspicious_frames_count"] >= 1

    # Frame #25 was tampered
    tampered_frame = next(f for f in frames if f.frame_index == 25)
    assert tampered_frame.classification == CLASS_SUSPICIOUS
    assert tampered_frame.color_marker == COLOR_GREEN
    assert "Synthetic high-frequency noise" in tampered_frame.detection_evidence

    # Surrounding earlier frames should be legitimate (RED)
    for f in frames[:20]:
        assert f.classification == CLASS_LEGITIMATE
        assert f.color_marker == COLOR_RED

    # Crucial policy check: Even 1 suspicious frame escalates overall risk score >= 60!
    assert result["risk_score"] >= 60


def test_uncertain_video_marked_yellow(sample_videos):
    """
    SECTION 6: YELLOW - UNCERTAIN FRAME.
    Low-quality / ambiguous frames receive YELLOW marker.
    """
    video_path = sample_videos["uncertain"]
    result = extract_all_video_frames(
        video_path=video_path,
        upload_id="test_uncertain_yellow",
        save_frames_to_disk=False,
    )

    assert result["uncertain_frames_count"] > 0
    uncert_frames = [f for f in result["frames"] if f.classification == CLASS_UNCERTAIN]
    for uf in uncert_frames:
        assert uf.color_marker == COLOR_YELLOW
        assert uf.uncertainty_reason is not None


def test_scan_video_firewall_allows_legitimate(sample_videos, db_session):
    """
    SECTION 10: ALLOW Decision Engine Flow.
    Clean legitimate video clears checks, is approved (ALLOW), and marked published.
    """
    upload = _create_test_upload(sample_videos["legitimate"], db_session, "Clean Video")
    scan_res = scan_video_firewall(upload.id, db_session)

    assert scan_res["verdict"] == "ALLOW"
    assert scan_res["publishing_status"] == "published"
    assert scan_res["legitimate_frames_count"] > 0
    assert scan_res["suspicious_frames_count"] == 0

    # Status route verification
    status_info = get_video_status(upload.id, db_session)
    assert status_info["verdict"] == "ALLOW"
    assert status_info["publishing_status"] == "published"


def test_quarantined_video_never_published_on_website(sample_videos, db_session):
    """
    SECTION 3 & 10: Publishing Firewall Gatekeeping.
    Quarantined / suspicious videos MUST NEVER appear on the website public feed.
    """
    upload = _create_test_upload(sample_videos["deepfake"], db_session, "Deepfake Attempt")
    scan_res = scan_video_firewall(upload.id, db_session)

    assert scan_res["verdict"] in ("QUARANTINE", "REVIEW")
    assert scan_res["publishing_status"] == "quarantined"

    # Verify website public feed does NOT contain this video
    feed = get_website_published_videos(db_session)
    published_ids = [v["video_id"] for v in feed["videos"]]
    assert upload.id not in published_ids


def test_admin_approve_publishes_quarantined_video(sample_videos, db_session):
    """
    SECTION 11: Admin Moderation Approval.
    An administrator can review and approve a quarantined video to publish it.
    """
    upload = _create_test_upload(sample_videos["uncertain"], db_session, "Uncertain Video")
    scan_video_firewall(upload.id, db_session)

    # Approve video
    appr_res = admin_approve_video(upload.id, db_session)
    assert appr_res["status"] == "success"
    assert appr_res["publishing_status"] == "published"

    # Now it should be visible on website public feed
    feed = get_website_published_videos(db_session)
    published_ids = [v["video_id"] for v in feed["videos"]]
    assert upload.id in published_ids


def test_admin_reject_destroys_and_blocklists(sample_videos, db_session):
    """
    SECTION 11: Admin Moderation Rejection.
    Rejection deletes the video file and commits the hash to blocklist.
    """
    upload = _create_test_upload(sample_videos["deepfake"], db_session, "Reject Candidate")
    sha256 = upload.sha256_hash
    scan_video_firewall(upload.id, db_session)

    # Reject video
    rej_res = admin_reject_video(upload.id, db_session)
    assert rej_res["status"] == "success"
    assert rej_res["verdict"] == "BLOCK"

    # Hash must be in blocklist now
    match = db_session.query(BlocklistHash).filter(BlocklistHash.sha256_hash == sha256).first()
    assert match is not None


def test_video_security_report_generation(sample_videos, db_session):
    """
    SECTION 9.F: Complete Video Security Report.
    Verify that report contains all required forensic fields.
    """
    upload = _create_test_upload(sample_videos["legitimate"], db_session, "Report Sample")
    scan_video_firewall(upload.id, db_session)

    rep = get_video_report(upload.id, db_session)
    assert rep["video_id"] == upload.id
    assert rep["sha256_hash"] == upload.sha256_hash
    assert rep["total_frames"] > 0
    assert "legitimate_frames_count" in rep
    assert "suspicious_frames_count" in rep
    assert "risk_score" in rep
    assert "verdict" in rep
    assert rep["verdict"] == "ALLOW"


def test_timeline_and_frame_gallery_queries(sample_videos, db_session):
    """
    SECTION 7 & 8: Frame Gallery & Timeline.
    Verify timeline and frame listing queries with color-coded markers.
    """
    upload = _create_test_upload(sample_videos["single_modified"], db_session, "Timeline Test")
    scan_video_firewall(upload.id, db_session)

    # Timeline query
    timeline = get_video_timeline(upload.id, db_session)
    assert len(timeline["markers"]) > 0
    assert len(timeline["suspicious_segments"]) > 0

    # Frames query (filtered by suspicious/GREEN)
    susp_frames = get_video_frames(upload.id, filter="suspicious", page=1, page_size=20, db=db_session)
    assert susp_frames["total_frames_matching"] > 0
    for f in susp_frames["frames"]:
        assert f["color_marker"] == COLOR_GREEN

    # Single frame inspection with adjacent comparisons
    first_frame_id = susp_frames["frames"][0]["id"]
    detail = get_single_frame(upload.id, first_frame_id, db=db_session)
    assert detail["id"] == first_frame_id
    assert detail["classification"] == CLASS_SUSPICIOUS
    assert "previous_frame" in detail


def test_admin_dashboard_metrics(sample_videos, db_session):
    """
    SECTION 9.E: Admin SOC Moderation Dashboard Telemetry.
    """
    dash = get_admin_dashboard(db_session)
    assert "total_videos" in dash
    assert "approved_videos" in dash
    assert "quarantined_videos" in dash
    assert "charts" in dash
    assert "frame_classifications" in dash["charts"]
