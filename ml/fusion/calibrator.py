"""
SafeGate Calibrated Score Fusion Layer.
Applies temperature-scaled fusion across spatial, frequency, and temporal branches,
and quantifies epistemic and aleatoric predictive uncertainty.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ml.detectors.pipeline import MultiBranchFrameResult


@dataclass(frozen=True)
class FusedFrameScores:
    frame_index: int
    timestamp_ms: int
    manipulation_score: float  # [0.0, 1.0]
    sensitive_score: float  # [0.0, 1.0]
    uncertainty_score: float  # [0.0, 1.0]
    is_blood_detected: bool
    is_nudity_detected: bool
    branch_contributions: dict[str, float]
    cues: dict[str, Any]


def _logit(p: float, eps: float = 1e-5) -> float:
    """Computes log-odds of a probability with boundary epsilon."""
    p_clipped = np.clip(p, eps, 1.0 - eps)
    return float(np.log(p_clipped / (1.0 - p_clipped)))


def _sigmoid(z: float) -> float:
    """Standard logistic sigmoid function."""
    return float(1.0 / (1.0 + np.exp(-z)))


class ScoreCalibrator:
    """
    Calibrates raw detector branch scores using temperature scaling and variance analysis.
    """

    def __init__(self, temperature: float = 1.25) -> None:
        self.temperature = max(0.1, temperature)

    def calibrate_and_fuse(
        self,
        raw_result: MultiBranchFrameResult,
        is_single_frame: bool = False,
    ) -> FusedFrameScores:
        """
        Combines multi-branch features into calibrated manipulation, sensitive, and uncertainty scores.
        """
        s_spatial = raw_result.spatial.manipulation_score
        s_freq = raw_result.frequency.manipulation_score
        s_temp = raw_result.temporal.anomaly_score

        # Determine dynamic branch weights
        if is_single_frame or raw_result.temporal.is_first_frame:
            # Single frame or video first frame: temporal branch inactive
            if raw_result.spatial.face_detected:
                w_spatial, w_freq, w_temp = 0.65, 0.35, 0.0
            else:
                w_spatial, w_freq, w_temp = 0.40, 0.60, 0.0
        else:
            if raw_result.spatial.face_detected:
                w_spatial, w_freq, w_temp = 0.50, 0.25, 0.25
            else:
                w_spatial, w_freq, w_temp = 0.35, 0.40, 0.25

        # Temperature-scaled logit fusion
        z_spatial = _logit(s_spatial)
        z_freq = _logit(s_freq)
        z_temp = _logit(s_temp) if w_temp > 0 else 0.0

        fused_logit = (w_spatial * z_spatial + w_freq * z_freq + w_temp * z_temp) / self.temperature
        manipulation_score = float(np.clip(_sigmoid(fused_logit), 0.0, 1.0))

        # Epistemic uncertainty: variance across active detector branches
        active_scores = [s_spatial, s_freq]
        if w_temp > 0:
            active_scores.append(s_temp)

        branch_variance = float(np.std(active_scores))

        # Aleatoric uncertainty / boundary ambiguity:
        # Highest when score is in the ambiguous decision region [0.35, 0.75]
        if 0.35 <= manipulation_score <= 0.75:
            entropy_factor = float(
                -manipulation_score * np.log(max(manipulation_score, 1e-5))
                - (1.0 - manipulation_score) * np.log(max(1.0 - manipulation_score, 1e-5))
            )
            normalized_entropy = float(entropy_factor / np.log(2.0))
        else:
            normalized_entropy = 0.0

        # Composite uncertainty score [0.0, 1.0]
        raw_uncertainty = 0.6 * branch_variance * 2.0 + 0.4 * normalized_entropy
        uncertainty_score = float(np.clip(raw_uncertainty, 0.0, 1.0))

        # Sensitive score remains strictly isolated
        sensitive_score = raw_result.sensitive.sensitive_score

        contributions = {
            "spatial": round(s_spatial, 4),
            "frequency": round(s_freq, 4),
            "temporal": round(s_temp, 4),
            "weight_spatial": round(w_spatial, 2),
            "weight_frequency": round(w_freq, 2),
            "weight_temporal": round(w_temp, 2),
        }

        return FusedFrameScores(
            frame_index=raw_result.frame_index,
            timestamp_ms=raw_result.timestamp_ms,
            manipulation_score=round(manipulation_score, 4),
            sensitive_score=round(sensitive_score, 4),
            uncertainty_score=round(uncertainty_score, 4),
            is_blood_detected=raw_result.sensitive.is_blood_detected,
            is_nudity_detected=raw_result.sensitive.is_nudity_detected,
            branch_contributions=contributions,
            cues=raw_result.cues,
        )
