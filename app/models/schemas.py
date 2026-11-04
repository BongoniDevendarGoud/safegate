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


# =============================================================================
# SafeGate 2.0 Extended Schemas: Video Upload Firewall & Frame-Level Detection
# =============================================================================

class VideoFrameItem(BaseModel):
    """Detailed metadata and forensic classification for a single extracted frame."""
    id: str
    upload_id: str
    frame_index: int
    timestamp_sec: float
    timestamp_str: str
    classification: str = Field(..., description="'LEGITIMATE', 'SUSPICIOUS', or 'UNCERTAIN'")
    color_marker: str = Field(..., description="'RED', 'GREEN', or 'YELLOW'")
    model_verdict: Optional[str] = None
    confidence: Optional[float] = None
    anomaly_score: Optional[float] = None
    detection_evidence: Optional[str] = None
    uncertainty_reason: Optional[str] = None
    sha256_hash: Optional[str] = None
    thumbnail_url: Optional[str] = None
    full_frame_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class VideoStatusResponse(BaseModel):
    """Real-time progress and telemetry for live video screening."""
    video_id: str
    status: str = Field(..., description="'pending', 'extracting', 'classifying', 'completed', 'failed'")
    verdict: Optional[str] = Field(None, description="'ALLOW', 'QUARANTINE', or 'BLOCK'")
    explanation: Optional[str] = None
    progress_percent: float = 0.0
    current_stage: str = "Intake"
    total_frames: int = 0
    extracted_frames: int = 0
    classified_frames: int = 0
    legitimate_frames_count: int = 0
    suspicious_frames_count: int = 0
    uncertain_frames_count: int = 0
    risk_score: int = 0
    elapsed_time_sec: float = 0.0
    model_name: Optional[str] = "SafeGate Dual-Engine Vision AI (PyTorch + Heuristic)"
    model_status: Optional[str] = "active"


class TimelineSegment(BaseModel):
    """Grouped contiguous sequence of frames with shared forensic classification."""
    segment_id: int
    start_frame: int
    end_frame: int
    start_time: str
    end_time: str
    frame_count: int
    classification: str
    color: str
    peak_anomaly: float
    reasons: List[str] = Field(default_factory=list)


class VideoTimelineResponse(BaseModel):
    """Complete video temporal timeline with colored frame markers and suspicious segments."""
    video_id: str
    duration_sec: float
    fps: float
    total_frames: int
    markers: List[Dict[str, Any]] = Field(default_factory=list)
    suspicious_segments: List[TimelineSegment] = Field(default_factory=list)


class VideoSecurityReport(BaseModel):
    """Comprehensive downloadable cryptographic video security report."""
    video_id: str
    filename: str
    sha256_hash: str
    file_size: int
    duration_sec: float
    resolution: str
    fps: float
    total_frames: int
    extracted_frames: int
    classified_frames: int
    legitimate_frames_count: int
    suspicious_frames_count: int
    uncertain_frames_count: int
    suspicious_timestamps: List[str] = Field(default_factory=list)
    suspicious_frame_references: List[Dict[str, Any]] = Field(default_factory=list)
    ai_model_name: str
    ai_model_status: str
    ai_model_outputs: Dict[str, Any] = Field(default_factory=dict)
    detection_evidence: List[str] = Field(default_factory=list)
    risk_score: int
    verdict: str  # ALLOW, QUARANTINE, or BLOCK
    publishing_status: str
    created_at: Optional[datetime] = None


class AdminDashboardResponse(BaseModel):
    """Security operations center (SOC) aggregated metrics and charts."""
    total_videos: int
    approved_videos: int
    quarantined_videos: int
    blocked_videos: int
    total_extracted_frames: int
    suspicious_frames_detected: int
    uncertain_frames: int
    recent_security_events: List[Dict[str, Any]] = Field(default_factory=list)
    charts: Dict[str, Any] = Field(default_factory=dict)


class WebsiteVideoItem(BaseModel):
    """Approved/published video exposed to the demo video-sharing website."""
    video_id: str
    title: str
    description: Optional[str] = None
    duration_sec: float
    fps: float
    resolution: str
    thumbnail_url: str
    stream_url: str
    verification_badge: str = "SafeGate Verified: Authentic Capture"
    published_at: Optional[datetime] = None
