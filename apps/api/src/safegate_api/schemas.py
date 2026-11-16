"""
SafeGate API Contract Schemas (Pydantic v2).
Defines request and response shapes for media intake, status, verdicts, and audit reports.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    upload_id: str = Field(description="Unique SafeGate asset identifier")
    tenant_id: str = Field(description="Host application tenant identifier")
    filename: str = Field(description="Original sanitized filename")
    mime_type: str = Field(description="Verified MIME type determined by magic bytes")
    file_size_bytes: int = Field(description="Total uploaded payload size in bytes")
    sha256_hash: str = Field(description="Cryptographic SHA-256 digest of binary media")
    status: str = Field(description="Processing status: QUEUED, PROCESSING, COMPLETED, FAILED")
    verdict: str = Field(
        description="Immediate or initial verdict: ALLOW, BLOCK, HUMAN_REVIEW, PENDING"
    )
    message: str = Field(description="Human-readable status summary")


class FrameScoreSummary(BaseModel):
    frame_index: int = Field(description="Zero-indexed frame sequence number")
    timestamp_ms: int = Field(description="Timestamp in milliseconds from media start")
    color: str = Field(description="Assigned frame classification: RED, YELLOW, GREEN")
    deepfake_score: float = Field(
        description="Calibrated probability of synthetic manipulation [0, 1]"
    )
    sensitive_score: float = Field(
        description="Calibrated probability of sensitive/graphic content [0, 1]"
    )
    uncertainty_score: float = Field(
        description="Model predictive uncertainty / ensemble entropy [0, 1]"
    )
    cues: dict[str, Any] = Field(
        default_factory=dict, description="Diagnostic cues and anomaly labels"
    )


class UploadStatusResponse(BaseModel):
    upload_id: str
    tenant_id: str
    filename: str
    mime_type: str
    sha256_hash: str
    status: str
    verdict: str
    total_frames: int
    red_frames: int
    yellow_frames: int
    green_frames: int
    frames: list[FrameScoreSummary] = Field(default_factory=list)
    published_url: str | None = None
    created_at: str
    completed_at: str | None = None


class AuditVerifyResponse(BaseModel):
    is_valid: bool = Field(description="True if HMAC hash chain is intact from genesis to tip")
    total_records: int = Field(description="Count of verified immutable event records")
    last_sequence: int = Field(description="Sequence number of the latest verified ledger record")
    last_signature: str = Field(description="HMAC-SHA256 signature at the head of the chain")
    verified_at: str = Field(description="UTC ISO 8601 timestamp of verification execution")


class HealthCheckResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    environment: str
    fail_closed_mode: bool
    database_connected: bool
