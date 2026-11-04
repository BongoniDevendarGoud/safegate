"""
SafeGate — Pydantic Validation & API Schemas
=============================================
Defines incoming request payloads and outgoing response structures.
Ensures strict type validation, prevents data leakage, and provides
standardized responses for documentation and client apps.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class UploadResponse(BaseModel):
    """Returned upon video upload and pipeline evaluation."""
    upload_id: str = Field(..., description="Unique 32-character hexadecimal UUID of the upload")
    verdict: str = Field(..., description="Final pipeline verdict: BLOCK, REVIEW, or ALLOW")
    explanation: str = Field(..., description="Plain-English explanation detailing the triggered stage")
    scan_duration_sec: Optional[float] = Field(None, description="Total screening pipeline runtime in seconds")
    nsfw_worst_score: Optional[float] = Field(None, description="Highest NSFW confidence score encountered (0.0 - 1.0)")
    deepfake_risk_score: Optional[int] = Field(None, description="Composite deepfake risk score (0 - 100)")
    total_frames_extracted: Optional[int] = Field(None, description="Total frames extracted at 24fps")
    legitimate_frames_count: Optional[int] = Field(None, description="Total frames marked legitimate (red mark)")
    modified_frames_count: Optional[int] = Field(None, description="Total frames marked modified")
    frames: Optional[List[Dict[str, Any]]] = Field(None, description="List of 24 frames per second with legitimate red markings")

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):
    """Standardized error format ensuring internal exceptions and stack traces are suppressed."""
    detail: str = Field(..., description="Human-readable safe error message")


class DecisionRecord(BaseModel):
    """Full detail of an upload decision used by moderator views."""
    id: str
    original_filename: str
    file_size: int
    sha256_hash: Optional[str] = None
    verdict: Optional[str] = None
    explanation: Optional[str] = None
    nsfw_worst_score: Optional[float] = None
    nsfw_worst_timestamp: Optional[float] = None
    deepfake_risk_score: Optional[int] = None
    deepfake_reasons: Optional[str] = None
    gemini_result: Optional[str] = None
    scan_duration_sec: Optional[float] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AuditVerifyResponse(BaseModel):
    """Integrity check status for the cryptographic audit log hash chain."""
    valid: bool = Field(..., description="True if the entire sequential hash chain is mathematically intact")
    total_entries: int = Field(..., description="Number of sequential audit log rows verified")
    broken_at: Optional[int] = Field(None, description="Row ID where a hash mismatch occurred, if any")
    message: str = Field(..., description="Verification summary statement")


class ReviewAction(BaseModel):
    """Payload for moderator approving or rejecting an upload in the review queue."""
    note: Optional[str] = Field(None, max_length=500, description="Optional moderator rationale or context")


class AppealResolve(BaseModel):
    """Payload for resolving a user appeal."""
    status: str = Field(..., pattern="^(approved|rejected)$", description="Resolved status: 'approved' or 'rejected'")
    moderator_note: Optional[str] = Field(None, max_length=500, description="Reasoning for the appeal resolution")


class AppealCreate(BaseModel):
    """Request payload submitted by a user appealing a verdict."""
    upload_id: str = Field(..., min_length=32, max_length=32, description="32-character UUID upload ID")
    reason: str = Field(..., min_length=10, max_length=2000, description="Detailed explanation of the appeal")


class AppealResponse(BaseModel):
    """Status details of a submitted appeal."""
    id: int
    upload_id: str
    reason: str
    status: str
    moderator_note: Optional[str] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StatsResponse(BaseModel):
    """Aggregated screening metrics for dashboard telemetry."""
    total_scanned: int
    total_blocked: int
    total_reviewed: int
    total_allowed: int
    avg_scan_time_sec: float
    verdicts_over_time: List[Dict[str, Any]] = Field(default_factory=list)
