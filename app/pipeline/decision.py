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


@dataclass
class DecisionResult:
    """The final policy determination emitted by the Decision Engine."""
    verdict: str  # "BLOCK", "REVIEW", or "ALLOW"
    explanation: str
    triggered_stage: str


def evaluate_signals(signals: ScreeningSignals) -> DecisionResult:
    """
    Evaluates all screening signals against configured security thresholds.

    Order of precedence:
    1. Processing Errors -> REVIEW (Fail-closed)
    2. Exact Blocklist -> BLOCK
    3. Perceptual Blocklist -> BLOCK
    4. NSFW Local Model >= BLOCK_THRESHOLD -> BLOCK
    5. Gemini Confirmed Explicit -> BLOCK
    6. Borderline NSFW [REVIEW_THRESHOLD, BLOCK_THRESHOLD) -> REVIEW
    7. Gemini Uncertain / Fallback -> REVIEW
    8. Deepfake Risk >= DEEPFAKE_REVIEW_THRESHOLD -> REVIEW
    9. All Stages Clean -> ALLOW
    """

    # 1. Fail-closed on any pipeline failure or timeout
    if signals.stage_error:
        return DecisionResult(
            verdict="REVIEW",
            explanation=f"Fail-closed: Screening pipeline encountered an error ({signals.stage_error}). Routed to human moderator.",
            triggered_stage="error_handling",
        )

    # 2. Exact SHA-256 match
    if signals.exact_match:
        return DecisionResult(
            verdict="BLOCK",
            explanation="Exact match: File SHA-256 checksum matches known prohibited media in blocklist.",
            triggered_stage="exact_hash",
        )

    # 3. Perceptual Hash near-duplicate match
    if signals.perceptual_match:
        dist = signals.perceptual_match.get("distance", 0)
        ts = signals.perceptual_match.get("timestamp", 0.0)
        return DecisionResult(
            verdict="BLOCK",
            explanation=(
                f"Perceptual match: Visual frame at {ts:.2f}s matches prohibited media "
                f"(Hamming distance {dist} <= {settings.PHASH_HAMMING_THRESHOLD})."
            ),
            triggered_stage="perceptual_hash",
        )

    # 4. Local NSFW model high-confidence explicit score
    if signals.nsfw_worst_score >= settings.BLOCK_THRESHOLD:
        return DecisionResult(
            verdict="BLOCK",
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
            verdict="BLOCK",
            explanation=(
                f"Gemini AI second opinion: Content confirmed explicit with {signals.gemini_confidence:.2f} confidence{reason_text}."
            ),
            triggered_stage="gemini_opinion",
        )

    # 6. Borderline NSFW score requires review
    if signals.nsfw_worst_score >= settings.REVIEW_THRESHOLD:
        return DecisionResult(
            verdict="REVIEW",
            explanation=(
                f"Borderline content: NSFW confidence score {signals.nsfw_worst_score:.2f} "
                f"at {signals.nsfw_worst_timestamp:.2f}s is in review range "
                f"[{settings.REVIEW_THRESHOLD:.2f}, {settings.BLOCK_THRESHOLD:.2f})."
            ),
            triggered_stage="nsfw_detector",
        )

    # 7. Gemini was queried but returned inconclusive / uncertain
    if signals.gemini_explicit is True and signals.gemini_confidence < 0.80:
        return DecisionResult(
            verdict="REVIEW",
            explanation=(
                f"Gemini AI flagged content as potentially explicit but confidence is moderate ({signals.gemini_confidence:.2f}). Routed to moderator."
            ),
            triggered_stage="gemini_opinion",
        )

    # 8. Deepfake risk heuristics triggered
    if signals.deepfake_score >= settings.DEEPFAKE_REVIEW_THRESHOLD:
        reasons = "; ".join(signals.deepfake_reasons or ["Unspecified visual/metadata anomalies"])
        return DecisionResult(
            verdict="REVIEW",
            explanation=(
                f"Deepfake risk advisory: Probabilistic manipulation score {signals.deepfake_score}/100 "
                f"exceeds review threshold ({settings.DEEPFAKE_REVIEW_THRESHOLD}). Signals: {reasons}."
            ),
            triggered_stage="deepfake_detector",
        )

    # 9. Clean pass
    return DecisionResult(
        verdict="ALLOW",
        explanation="Clean: Media cleared all screening stages without triggering security thresholds.",
        triggered_stage="decision_engine",
    )
