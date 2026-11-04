"""
SafeGate — SQLAlchemy ORM Database Models
===========================================
Defines the schema for SQLite storage:
1. Upload: Tracks every video upload, lifecycle state, hashes, and detector verdicts.
2. BlocklistHash: Exact SHA-256 matches of previously blocked media.
3. BlocklistPHash: Perceptual hashes (pHash) of prohibited visual frames for fuzzy deduplication.
4. AuditLog: Tamper-evident sequential audit log with cryptographic hash chaining.
5. Appeal: User appeals submitted for moderator evaluation.

VIVA EXPLANATION:
- We never store explicit media. On a BLOCK verdict, the raw file is destroyed,
  and only mathematical fingerprints (SHA-256 and pHashes) are retained.
- The primary key for uploads is a 32-character UUID hex string, preventing
  sequential ID enumeration attacks (OWASP IDOR).
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
)
from app.db import Base


def _gen_uuid_hex() -> str:
    """Generate a non-sequential 32-character hexadecimal UUID4 string."""
    return uuid.uuid4().hex


def _now_utc() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class Upload(Base):
    """
    Records the metadata and screening lifecycle for every uploaded video file.
    """
    __tablename__ = "uploads"

    # Cryptographically unpredictable 32-character UUID identifier
    id = Column(String(32), primary_key=True, default=_gen_uuid_hex, index=True)

    # Original filename from user (stored solely for moderator display, NEVER used in filesystem paths)
    original_filename = Column(String(255), nullable=False)

    # Sanitized UUID-based filename on disk inside quarantine/, review/, or published/
    stored_filename = Column(String(255), nullable=False)

    # Size in bytes
    file_size = Column(Integer, nullable=False)

    # Exact SHA-256 checksum (64 hex characters)
    sha256_hash = Column(String(64), nullable=True, index=True)

    # Final verdict: "BLOCK", "REVIEW", or "ALLOW"
    verdict = Column(String(10), nullable=True, index=True)

    # Human-readable rationale detailing which pipeline stage triggered the decision
    explanation = Column(Text, nullable=True)

    # Worst NSFW classification confidence score encountered across all extracted frames (0.0 - 1.0)
    nsfw_worst_score = Column(Float, nullable=True)

    # Timestamp in seconds where the peak NSFW score occurred
    nsfw_worst_timestamp = Column(Float, nullable=True)

    # Composite probabilistic deepfake risk score (0 - 100, advisory only)
    deepfake_risk_score = Column(Integer, nullable=True)

    # Structured JSON string of triggered deepfake heuristics and rationales
    deepfake_reasons = Column(Text, nullable=True)

    # Structured JSON response from Gemini second opinion (if invoked)
    gemini_result = Column(Text, nullable=True)

    # Total scan runtime in seconds
    scan_duration_sec = Column(Float, nullable=True)

    # --- SafeGate 2.0 Extended Firewall Metadata ---
    # Video metadata
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    duration_sec = Column(Float, nullable=True)
    fps = Column(Float, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    # Frame extraction & classification counters
    total_frames = Column(Integer, nullable=True, default=0)
    extracted_frames = Column(Integer, nullable=True, default=0)
    classified_frames = Column(Integer, nullable=True, default=0)
    failed_frames = Column(Integer, nullable=True, default=0)
    legitimate_frames_count = Column(Integer, nullable=True, default=0)
    suspicious_frames_count = Column(Integer, nullable=True, default=0)
    uncertain_frames_count = Column(Integer, nullable=True, default=0)

    # Overall video risk score (0 - 100)
    risk_score = Column(Integer, nullable=True, default=0)

    # Website publishing state: "unpublished", "published", "quarantined", "rejected"
    publishing_status = Column(String(32), nullable=False, default="unpublished", index=True)

    # Grouped suspicious segments (JSON array)
    suspicious_segments = Column(Text, nullable=True)

    # AI Model diagnostics
    model_name = Column(String(128), nullable=True)
    model_status = Column(String(64), nullable=True, default="active")

    # Complete downloadable video security report (JSON)
    security_report_json = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=_now_utc, nullable=False)
    updated_at = Column(DateTime, default=_now_utc, onupdate=_now_utc, nullable=True)


class VideoFrame(Base):
    """
    SafeGate 2.0 — Individual Extracted Video Frame Record.
    Enforces the exact color classification scheme:
      - RED    = LEGITIMATE / AUTHENTIC FRAME
      - GREEN  = SUSPICIOUS / AI-MANIPULATED FRAME
      - YELLOW = UNCERTAIN FRAME
    """
    __tablename__ = "video_frames"

    id = Column(String(36), primary_key=True, default=_gen_uuid_hex, index=True)
    upload_id = Column(String(32), ForeignKey("uploads.id"), nullable=False, index=True)
    frame_index = Column(Integer, nullable=False, index=True)
    timestamp_sec = Column(Float, nullable=False)
    timestamp_str = Column(String(32), nullable=False)

    # Classification & Color Mapping (strictly enforced)
    classification = Column(String(32), nullable=False, index=True)  # "LEGITIMATE", "SUSPICIOUS", "UNCERTAIN"
    color_marker = Column(String(16), nullable=False, index=True)    # "RED", "GREEN", "YELLOW"

    # AI Model Output & Evidence
    model_verdict = Column(String(128), nullable=True)
    confidence = Column(Float, nullable=True)
    anomaly_score = Column(Float, nullable=True)
    detection_evidence = Column(Text, nullable=True)
    uncertainty_reason = Column(Text, nullable=True)

    # Cryptographic integrity & storage references
    sha256_hash = Column(String(64), nullable=True)
    thumbnail_path = Column(String(512), nullable=True)
    frame_file_path = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=_now_utc, nullable=False)


class BlocklistHash(Base):
    """
    Exact-match blocklist of SHA-256 hashes for known prohibited files.
    """
    __tablename__ = "blocklist_hashes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sha256_hash = Column(String(64), unique=True, nullable=False, index=True)
    source = Column(String(64), nullable=False, default="auto-block")  # "auto-block" or "admin"
    created_at = Column(DateTime, default=_now_utc, nullable=False)


class BlocklistPHash(Base):
    """
    Fuzzy-match blocklist of 16-character hexadecimal perceptual hashes (pHash).
    Matches frames that have undergone minor transformations, re-encodings, or watermarking.
    """
    __tablename__ = "blocklist_phashes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phash_hex = Column(String(16), nullable=False, index=True)
    source = Column(String(64), nullable=False, default="auto-block")
    created_at = Column(DateTime, default=_now_utc, nullable=False)


class AuditLog(Base):
    """
    Tamper-evident audit log implementing a cryptographic hash chain.
    
    Each row records:
    row_hash = SHA256(previous_hash + action + details + timestamp)
    Any retrospective modification or deletion of rows invalidates the chain.
    """
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(128), nullable=False)
    details = Column(Text, nullable=True)
    upload_id = Column(String(32), ForeignKey("uploads.id"), nullable=True)
    row_hash = Column(String(64), nullable=False)
    previous_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=_now_utc, nullable=False)


class Appeal(Base):
    """
    Represents an appeal submitted by a user against a BLOCK or REVIEW verdict.
    """
    __tablename__ = "appeals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(String(32), ForeignKey("uploads.id"), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pending")  # pending, approved, rejected
    moderator_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now_utc, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
