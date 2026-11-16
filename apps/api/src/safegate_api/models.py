"""
SafeGate SQLAlchemy 2.0 Async Models.
Defines schema for MediaUpload, FrameAnalysis, and AuditLedgerEntry.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from safegate_api.database import Base


class MediaUpload(Base):
    __tablename__ = "media_uploads"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    is_video: Mapped[bool] = mapped_column(Boolean, nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="QUEUED", nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)

    quarantine_key: Mapped[str] = mapped_column(String(255), nullable=False)
    published_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    total_frames: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    red_frame_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    yellow_frame_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    green_frame_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship to extracted frame analyses
    frames: Mapped[list[FrameAnalysis]] = relationship(
        "FrameAnalysis", back_populates="upload", cascade="all, delete-orphan"
    )


class FrameAnalysis(Base):
    __tablename__ = "frame_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("media_uploads.id"), index=True, nullable=False
    )
    frame_index: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str] = mapped_column(String(16), nullable=False)  # RED, YELLOW, GREEN

    deepfake_score: Mapped[float] = mapped_column(Float, nullable=False)
    sensitive_score: Mapped[float] = mapped_column(Float, nullable=False)
    uncertainty_score: Mapped[float] = mapped_column(Float, nullable=False)
    cues_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    upload: Mapped[MediaUpload] = relationship("MediaUpload", back_populates="frames")


class AuditLedgerEntry(Base):
    __tablename__ = "audit_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sequence_num: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    upload_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    prev_signature: Mapped[str] = mapped_column(String(64), nullable=False)
    signature: Mapped[str] = mapped_column(String(64), nullable=False)
