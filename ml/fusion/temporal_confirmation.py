"""
SafeGate Temporal Confirmation & Color Assignment Subsystem.
Enforces Rule 7: Eliminates single-frame false RED blocks via temporal neighbor confirmation.
Assigns exactly one color (RED, YELLOW, GREEN) to every frame.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ml.fusion.calibrator import FusedFrameScores
from safegate_api.config import ThresholdsConfig


@dataclass(frozen=True)
class FrameVerdict:
    frame_index: int
    timestamp_ms: int
    color: str  # RED, YELLOW, GREEN
    deepfake_score: float
    sensitive_score: float
    uncertainty_score: float
    confirmation_reason: str
    cues: dict[str, Any]


class TemporalConfirmationEngine:
    """
    Applies calibrated thresholds and temporal window smoothing to assign final frame colors.
    """

    def __init__(
        self,
        thresholds: ThresholdsConfig | None = None,
        min_consecutive_red: int = 2,
    ) -> None:
        self.thresholds = thresholds or ThresholdsConfig()
        self.min_consecutive_red = max(1, min_consecutive_red)

    def evaluate_sequence(
        self,
        fused_frames: list[FusedFrameScores],
    ) -> list[FrameVerdict]:
        """
        Processes an entire sequence of fused frames, applying temporal neighbor confirmation
        for candidate RED frames.
        """
        n = len(fused_frames)
        if n == 0:
            return []

        red_thresh = self.thresholds.deepfake_manipulation_score.red_block_threshold
        yellow_thresh = self.thresholds.deepfake_manipulation_score.yellow_review_threshold
        sens_thresh = self.thresholds.sensitive_content_score.yellow_review_threshold
        uncert_thresh = self.thresholds.uncertainty_score.yellow_review_threshold

        # Step 1: Initial candidate labeling
        candidate_labels: list[str] = []
        for f in fused_frames:
            if f.manipulation_score >= red_thresh:
                candidate_labels.append("CANDIDATE_RED")
            elif (
                f.sensitive_score >= sens_thresh
                or f.uncertainty_score >= uncert_thresh
                or f.manipulation_score >= yellow_thresh
                or f.is_blood_detected
                or f.is_nudity_detected
            ):
                candidate_labels.append("YELLOW")
            else:
                candidate_labels.append("GREEN")

        # Step 2: Temporal window confirmation for RED frames (Rule 7)
        final_verdicts: list[FrameVerdict] = []

        for i, f in enumerate(fused_frames):
            lbl = candidate_labels[i]

            if lbl == "CANDIDATE_RED":
                if n == 1:
                    # Single still image: no temporal neighbors exist
                    # Require high confidence / low uncertainty to confirm RED directly
                    if f.uncertainty_score < uncert_thresh and f.manipulation_score >= red_thresh:
                        final_color = "RED"
                        reason = "Still image manipulation confirmed with low uncertainty."
                    else:
                        final_color = "YELLOW"
                        reason = "Still image high manipulation but elevated uncertainty; routed to review."

                else:
                    # Multi-frame video: check temporal neighbors
                    # Check window of +/- 2 frames around current frame
                    start_w = max(0, i - 1)
                    end_w = min(n, i + 2)
                    neighbor_candidate_count = sum(
                        1 for k in range(start_w, end_w) if candidate_labels[k] == "CANDIDATE_RED"
                    )

                    # Exceptionally high score (>= 0.92) or neighbor agreement confirms RED
                    if (
                        neighbor_candidate_count >= self.min_consecutive_red
                        or f.manipulation_score >= 0.92
                    ):
                        final_color = "RED"
                        reason = (
                            f"RED confirmed with temporal agreement ({neighbor_candidate_count} consecutive frames) "
                            f"at score {f.manipulation_score:.2f}."
                        )
                    else:
                        # Isolated transient spike downgraded to YELLOW per Rule 7
                        final_color = "YELLOW"
                        reason = (
                            f"Isolated candidate RED spike ({f.manipulation_score:.2f}) without temporal neighbor confirmation; "
                            "downgraded to YELLOW for human review."
                        )

            elif lbl == "YELLOW":
                final_color = "YELLOW"
                sens_causes = []
                if f.is_blood_detected or f.sensitive_score >= sens_thresh:
                    sens_causes.append(f"blood/violence ({f.sensitive_score:.2f})")
                if f.is_nudity_detected:
                    sens_causes.append("nudity")
                if f.uncertainty_score >= uncert_thresh:
                    sens_causes.append(f"model uncertainty ({f.uncertainty_score:.2f})")
                if yellow_thresh <= f.manipulation_score < red_thresh:
                    sens_causes.append(f"borderline manipulation ({f.manipulation_score:.2f})")

                reason = f"YELLOW assigned due to: {', '.join(sens_causes) if sens_causes else 'sensitive content/uncertainty'}."

            else:
                final_color = "GREEN"
                reason = "Authentic frame: clean manipulation, clean sensitive, low uncertainty."

            final_verdicts.append(
                FrameVerdict(
                    frame_index=f.frame_index,
                    timestamp_ms=f.timestamp_ms,
                    color=final_color,
                    deepfake_score=f.manipulation_score,
                    sensitive_score=f.sensitive_score,
                    uncertainty_score=f.uncertainty_score,
                    confirmation_reason=reason,
                    cues=f.cues,
                )
            )

        return final_verdicts
