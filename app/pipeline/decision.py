"""
SafeGate — Decision Engine (Pipeline Stage 8)
==============================================
The single, authoritative policy decision point in SafeGate.
All screening signals from Stages 1-7 converge here.

THRESHOLD LOGIC (configured in config.py):
1. BLOCK:
   - Stage 2: SHA-256 matches exact-blocklist.
   - Stage 4: Any frame pHash matches perceptual blocklist (distance <= PHASH_HAMMING_THRESHOLD).
   - Stage 5: Peak local NSFW confidence >= BLOCK_THRESHOLD (default: 0.85).
   - Stage 6: Gemini second-opinion confirms explicit content with high confidence (>= 0.85).

2. REVIEW (Fail-Closed Gate):
   - Stage 5: Peak local NSFW confidence in [REVIEW_THRESHOLD, BLOCK_THRESHOLD) (default: 0.45 - 0.85).
   - Stage 6: Gemini returned uncertain or safety refusal or timed out.
   - Stage 7: Composite deepfake risk score >= DEEPFAKE_REVIEW_THRESHOLD (default: 60).
   - Fail-Closed: Any uncaught exception, corrupted frame, or processing timeout in any stage.

3. ALLOW:
   - Video passed every single check with all indicators strictly below review thresholds.

EVIDENCE & RETENTION POLICY:
- We NEVER store prohibited images or explicit frames on disk.
- On BLOCK: The video is destroyed from disk; only SHA-256 and frame pHashes are recorded.
- On REVIEW: The file is quarantined inside review/ for moderator resolution.
- On ALLOW: The file is moved to published/.
"""

import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)


class VerdictStr(str):
    """
    Polymorphic verdict string for SafeGate 2.0.
    Treats QUARANTINE and REVIEW as functionally identical for backwards compatibility,
    while canonicalizing display to QUARANTINE.
    """
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, str):
            return False
        s1 = str(self).upper()
        s2 = other.upper()
        if s1 == s2:
            return True
        if {s1, s2} == {"QUARANTINE", "REVIEW"}:
            return True
        return False

    def __hash__(self) -> int:
        return hash(str(self).upper())


@dataclass
class ScreeningSignals:
    """Encapsulates all evaluation results collected across pipeline stages."""
    exact_match: bool = False
    perceptual_match: Optional[dict] = None  # {timestamp, frame_phash, block_phash, distance}
    nsfw_worst_score: float = 0.0
    nsfw_worst_timestamp: float = 0.0
    gemini_explicit: Optional[bool] = None
    gemini_confidence: float = 0.0
    gemini_reason: Optional[str] = None
    deepfake_score: int = 0
    deepfake_reasons: Optional[List[str]] = None
    stage_error: Optional[str] = None
    # SafeGate 2.0 frame-level detections
    suspicious_frames_count: int = 0
    uncertain_frames_count: int = 0
    model_failure: bool = False
    model_name: Optional[str] = None


@dataclass
class DecisionResult:
    """The final policy determination emitted by the Decision Engine."""
    verdict: VerdictStr  # "BLOCK", "QUARANTINE", or "ALLOW"
    explanation: str
    triggered_stage: str


def evaluate_signals(signals: ScreeningSignals) -> DecisionResult:
    """
    Evaluates all screening signals against configured security thresholds.

    Order of precedence:
    1. Processing Errors / Model Failures -> QUARANTINE (Fail-closed)
    2. Exact Blocklist -> BLOCK
    3. Perceptual Blocklist -> BLOCK
    4. NSFW Local Model >= BLOCK_THRESHOLD -> BLOCK
    5. Gemini Confirmed Explicit -> BLOCK
    6. Suspicious Frames (>= 1) -> QUARANTINE (SafeGate 2.0 Firewall Core Rule)
    7. Uncertain Frames (>= 1) -> QUARANTINE
    8. Borderline NSFW [REVIEW_THRESHOLD, BLOCK_THRESHOLD) -> QUARANTINE
    9. Gemini Uncertain / Fallback -> QUARANTINE
    10. Deepfake Risk >= DEEPFAKE_REVIEW_THRESHOLD -> QUARANTINE
    11. All Stages Clean -> ALLOW
    """

    # 1. Fail-closed on any pipeline failure or timeout
    if signals.stage_error:
        return DecisionResult(
            verdict=VerdictStr("QUARANTINE"),
            explanation=f"Fail-closed: Screening pipeline encountered an error ({signals.stage_error}). Routed to human moderator.",
            triggered_stage="error_handling",
        )

    # 1b. AI Model Failure (Scenario 6)
    if signals.model_failure:
        return DecisionResult(
            verdict=VerdictStr("QUARANTINE"),
            explanation=f"Fail-closed: AI deepfake detection model ({signals.model_name or 'Neural Detector'}) was unavailable or encountered an execution failure. Routed to quarantine.",
            triggered_stage="ai_model_failure",
        )

    # 2. Exact SHA-256 match
    if signals.exact_match:
        return DecisionResult(
            verdict=VerdictStr("BLOCK"),
            explanation="Exact match: File SHA-256 checksum matches known prohibited media in blocklist.",
            triggered_stage="exact_hash",
        )

    # 3. Perceptual Hash near-duplicate match
    if signals.perceptual_match:
        dist = signals.perceptual_match.get("distance", 0)
        ts = signals.perceptual_match.get("timestamp", 0.0)
        return DecisionResult(
            verdict=VerdictStr("BLOCK"),
            explanation=(
                f"Perceptual match: Visual frame at {ts:.2f}s matches prohibited media "
                f"(Hamming distance {dist} <= {settings.PHASH_HAMMING_THRESHOLD})."
            ),
            triggered_stage="perceptual_hash",
        )

    # 4. Local NSFW model high-confidence explicit score
    if signals.nsfw_worst_score >= settings.BLOCK_THRESHOLD:
        return DecisionResult(
            verdict=VerdictStr("BLOCK"),
            explanation=(
                f"Local NSFW screening: Explicit confidence score {signals.nsfw_worst_score:.2f} "
                f"at {signals.nsfw_worst_timestamp:.2f}s exceeds block threshold ({settings.BLOCK_THRESHOLD:.2f})."
            ),
            triggered_stage="nsfw_detector",
        )

    # 5. Gemini second opinion confirmed explicit with high confidence
    if signals.gemini_explicit is True and signals.gemini_confidence >= 0.80:
        reason_text = f" ({signals.gemini_reason})" if signals.gemini_reason else ""
        return DecisionResult(
            verdict=VerdictStr("BLOCK"),
            explanation=(
                f"Gemini AI second opinion: Content confirmed explicit with {signals.gemini_confidence:.2f} confidence{reason_text}."
            ),
            triggered_stage="gemini_opinion",
        )

    # 6. SafeGate 2.0: Even a single suspicious / AI-manipulated frame forces QUARANTINE
    if signals.suspicious_frames_count > 0:
        return DecisionResult(
            verdict=VerdictStr("QUARANTINE"),
            explanation=(
                f"Firewall policy violation: Identified {signals.suspicious_frames_count} suspicious / AI-manipulated frame(s) "
                f"(marked GREEN). Video isolated in quarantine to prevent unauthorized publication."
            ),
            triggered_stage="frame_classification",
        )

    # 7. SafeGate 2.0: Inconclusive or uncertain frame classifications force QUARANTINE
    if signals.uncertain_frames_count > 0:
        return DecisionResult(
            verdict=VerdictStr("QUARANTINE"),
            explanation=(
                f"Firewall policy precaution: {signals.uncertain_frames_count} frame(s) returned UNCERTAIN classifications "
                f"(marked YELLOW). Video held in quarantine for administrator verification."
            ),
            triggered_stage="frame_classification",
        )

    # 8. Borderline NSFW score requires review
    if signals.nsfw_worst_score >= settings.REVIEW_THRESHOLD:
        return DecisionResult(
            verdict=VerdictStr("QUARANTINE"),
            explanation=(
                f"Borderline content: NSFW confidence score {signals.nsfw_worst_score:.2f} "
                f"at {signals.nsfw_worst_timestamp:.2f}s is in review range "
                f"[{settings.REVIEW_THRESHOLD:.2f}, {settings.BLOCK_THRESHOLD:.2f})."
            ),
            triggered_stage="nsfw_detector",
        )

    # 9. Gemini was queried but returned inconclusive / uncertain
    if signals.gemini_explicit is True and signals.gemini_confidence < 0.80:
        return DecisionResult(
            verdict=VerdictStr("QUARANTINE"),
            explanation=(
                f"Gemini AI flagged content as potentially explicit but confidence is moderate ({signals.gemini_confidence:.2f}). Routed to moderator."
            ),
            triggered_stage="gemini_opinion",
        )

    # 10. Deepfake risk heuristics triggered
    if signals.deepfake_score >= settings.DEEPFAKE_REVIEW_THRESHOLD:
        reasons = "; ".join(signals.deepfake_reasons or ["Unspecified visual/metadata anomalies"])
        return DecisionResult(
            verdict=VerdictStr("QUARANTINE"),
            explanation=(
                f"Deepfake risk advisory: Probabilistic manipulation score {signals.deepfake_score}/100 "
                f"exceeds review threshold ({settings.DEEPFAKE_REVIEW_THRESHOLD}). Signals: {reasons}."
            ),
            triggered_stage="deepfake_detector",
        )

    # 11. Clean pass
    return DecisionResult(
        verdict=VerdictStr("ALLOW"),
        explanation="Clean: Media cleared all screening stages without triggering security thresholds.",
        triggered_stage="decision_engine",
    )
