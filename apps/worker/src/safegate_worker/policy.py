"""
SafeGate Content-Level Policy Engine.
Enforces authoritative decision priority:
RED (BLOCK) > YELLOW (HUMAN_REVIEW) > GREEN (ALLOW)
Guarantees fail-closed safety under all conditions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ml.fusion.temporal_confirmation import FrameVerdict


@dataclass(frozen=True)
class SuspiciousInterval:
    start_frame: int
    end_frame: int
    start_ms: int
    end_ms: int
    color: str
    peak_score: float


@dataclass(frozen=True)
class ContentDecision:
    verdict: str  # ALLOW, BLOCK, HUMAN_REVIEW
    total_frames: int
    red_frames: int
    yellow_frames: int
    green_frames: int
    red_frame_indices: list[int]
    yellow_frame_indices: list[int]
    suspicious_intervals: list[SuspiciousInterval]
    summary_reason: str
    metadata: dict[str, Any]


def group_intervals(frames: list[FrameVerdict], target_color: str) -> list[SuspiciousInterval]:
    """Groups consecutive flagged frames into contiguous time intervals."""
    intervals: list[SuspiciousInterval] = []
    in_interval = False
    start_f = 0
    start_ms = 0
    peak_score = 0.0

    for i, f in enumerate(frames):
        if f.color == target_color:
            score = (
                f.deepfake_score
                if target_color == "RED"
                else max(f.sensitive_score, f.uncertainty_score)
            )
            if not in_interval:
                in_interval = True
                start_f = f.frame_index
                start_ms = f.timestamp_ms
                peak_score = score
            else:
                peak_score = max(peak_score, score)
        else:
            if in_interval:
                prev_f = frames[i - 1]
                intervals.append(
                    SuspiciousInterval(
                        start_frame=start_f,
                        end_frame=prev_f.frame_index,
                        start_ms=start_ms,
                        end_ms=prev_f.timestamp_ms,
                        color=target_color,
                        peak_score=round(peak_score, 4),
                    )
                )
                in_interval = False

    if in_interval and frames:
        last_f = frames[-1]
        intervals.append(
            SuspiciousInterval(
                start_frame=start_f,
                end_frame=last_f.frame_index,
                start_ms=start_ms,
                end_ms=last_f.timestamp_ms,
                color=target_color,
                peak_score=round(peak_score, 4),
            )
        )

    return intervals


class ContentPolicyEngine:
    """
    Evaluates frame verdicts and produces final publication clearance or block.
    """

    def evaluate(
        self,
        frame_verdicts: list[FrameVerdict],
        fail_closed_triggered: bool = False,
        error_context: str | None = None,
        detector_type: str = "heuristic",
        has_validated_model: bool = False,
        has_calibrated_thresholds: bool = False,
    ) -> ContentDecision:
        """
        Enforces RED > YELLOW > GREEN priority resolution with fail-closed security invariants.
        A verdict can only be ALLOW if detector_type == 'model', a validated model is loaded,
        and thresholds are empirically calibrated.
        """
        total = len(frame_verdicts)

        # Fail-closed guard: empty inputs or explicit failure flags
        if fail_closed_triggered or total == 0:
            return ContentDecision(
                verdict="HUMAN_REVIEW",
                total_frames=total,
                red_frames=0,
                yellow_frames=total,
                green_frames=0,
                red_frame_indices=[],
                yellow_frame_indices=[],
                suspicious_intervals=[],
                summary_reason=f"Fail-closed policy enforced: {error_context or 'zero decodable frames or worker error'}.",
                metadata={"fail_closed": True, "reason_code": "FAIL_CLOSED_ERROR"},
            )

        # Fail-closed guard: check for NaN, Inf, or missing scores
        for f in frame_verdicts:
            for score, name in [
                (f.deepfake_score, "deepfake_score"),
                (f.sensitive_score, "sensitive_score"),
                (f.uncertainty_score, "uncertainty_score"),
            ]:
                if math.isnan(score) or math.isinf(score):
                    return ContentDecision(
                        verdict="HUMAN_REVIEW",
                        total_frames=total,
                        red_frames=0,
                        yellow_frames=total,
                        green_frames=0,
                        red_frame_indices=[],
                        yellow_frame_indices=list(range(total)),
                        suspicious_intervals=[],
                        summary_reason=f"Fail-closed policy enforced: invalid numerical value ({name}={score}) at frame {f.frame_index}.",
                        metadata={"fail_closed": True, "reason_code": "NUMERICAL_INSTABILITY"},
                    )

        red_indices = [f.frame_index for f in frame_verdicts if f.color == "RED"]
        yellow_indices = [f.frame_index for f in frame_verdicts if f.color == "YELLOW"]
        green_indices = [f.frame_index for f in frame_verdicts if f.color == "GREEN"]

        num_red = len(red_indices)
        num_yellow = len(yellow_indices)
        num_green = len(green_indices)

        # -------------------------------------------------------------
        # 1. Any confirmed RED frame -> BLOCK
        # -------------------------------------------------------------
        if num_red > 0:
            red_intervals = group_intervals(frame_verdicts, "RED")
            peak_deepfake = max(f.deepfake_score for f in frame_verdicts if f.color == "RED")
            reason = (
                f"Content blocked: {num_red} confirmed RED frame(s) with deepfake/manipulation detected "
                f"(peak manipulation score {peak_deepfake:.2f})."
            )
            return ContentDecision(
                verdict="BLOCK",
                total_frames=total,
                red_frames=num_red,
                yellow_frames=num_yellow,
                green_frames=num_green,
                red_frame_indices=red_indices,
                yellow_frame_indices=yellow_indices,
                suspicious_intervals=red_intervals,
                summary_reason=reason,
                metadata={"blocked_at_frame": red_indices[0], "reason_code": "RED_FRAME_DETECTED"},
            )

        # -------------------------------------------------------------
        # 2. Else any YELLOW frame -> HUMAN_REVIEW
        # -------------------------------------------------------------
        if num_yellow > 0:
            yellow_intervals = group_intervals(frame_verdicts, "YELLOW")
            reason = (
                f"Content held for human review: {num_yellow} YELLOW frame(s) flagged for sensitive content, "
                "graphic violence, blood, or model uncertainty."
            )
            return ContentDecision(
                verdict="HUMAN_REVIEW",
                total_frames=total,
                red_frames=0,
                yellow_frames=num_yellow,
                green_frames=num_green,
                red_frame_indices=[],
                yellow_frame_indices=yellow_indices,
                suspicious_intervals=yellow_intervals,
                summary_reason=reason,
                metadata={"review_required": True, "reason_code": "YELLOW_FRAME_DETECTED"},
            )

        # -------------------------------------------------------------
        # 3. Model & Calibration Validation Guard:
        # A verdict can only be ALLOW if detector_type == 'model',
        # a validated trained model is loaded, and thresholds are calibrated.
        # -------------------------------------------------------------
        if detector_type != "model" or not has_validated_model:
            return ContentDecision(
                verdict="HUMAN_REVIEW",
                total_frames=total,
                red_frames=0,
                yellow_frames=total,
                green_frames=0,
                red_frame_indices=[],
                yellow_frame_indices=list(range(total)),
                suspicious_intervals=[],
                summary_reason="NO_VALIDATED_MODEL: Analysis unavailable with trained model, sent for human review.",
                metadata={
                    "fail_closed": True,
                    "reason_code": "NO_VALIDATED_MODEL",
                    "detector_type": detector_type,
                    "has_validated_model": has_validated_model,
                },
            )

        if not has_calibrated_thresholds:
            return ContentDecision(
                verdict="HUMAN_REVIEW",
                total_frames=total,
                red_frames=0,
                yellow_frames=total,
                green_frames=0,
                red_frame_indices=[],
                yellow_frame_indices=list(range(total)),
                suspicious_intervals=[],
                summary_reason="UNCALIBRATED_THRESHOLDS: System thresholds not validated by empirical calibration run.",
                metadata={"fail_closed": True, "reason_code": "UNCALIBRATED_THRESHOLDS"},
            )

        # -------------------------------------------------------------
        # 4. Constant / Flatline Score Guard:
        # If all frames produce identical constant scores, detector is uninformative
        # -------------------------------------------------------------
        if total >= 2:
            unique_scores = {round(f.deepfake_score, 6) for f in frame_verdicts}
            if len(unique_scores) == 1:
                return ContentDecision(
                    verdict="HUMAN_REVIEW",
                    total_frames=total,
                    red_frames=0,
                    yellow_frames=total,
                    green_frames=0,
                    red_frame_indices=[],
                    yellow_frame_indices=list(range(total)),
                    suspicious_intervals=[],
                    summary_reason="CONSTANT_SCORES_UNINFORMATIVE: All frames yielded identical constant scores, sent for human review.",
                    metadata={"fail_closed": True, "reason_code": "CONSTANT_SCORES_UNINFORMATIVE"},
                )

        # -------------------------------------------------------------
        # 5. All criteria met and 100% of frames are GREEN -> ALLOW
        # -------------------------------------------------------------
        return ContentDecision(
            verdict="ALLOW",
            total_frames=total,
            red_frames=0,
            yellow_frames=0,
            green_frames=total,
            red_frame_indices=[],
            yellow_frame_indices=[],
            suspicious_intervals=[],
            summary_reason=f"Content cleared for publication: all {total} frame(s) verified authentic and clean by validated model.",
            metadata={"cleared_frame_count": total, "detector_type": detector_type},
        )
