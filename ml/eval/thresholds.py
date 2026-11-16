"""
SafeGate Calibrated Threshold Optimizer.
Selects optimal operational thresholds on validation data to achieve a specified
false-positive rate (FPR) target on authentic content.
Implements empirical threshold discovery and temperature scaling optimization.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ml.eval.metrics import compute_expected_calibration_error, compute_roc_curve


@dataclass(frozen=True)
class CalibratedThresholdResult:
    target_fpr: float
    achieved_fpr: float
    achieved_tpr: float
    optimal_red_threshold: float
    recommended_yellow_threshold: float
    optimal_temperature: float
    ece_before: float
    ece_after: float
    validation_sample_count: int


class ThresholdCalibrator:
    """Discovers operational thresholds and optimal temperature from validation runs."""

    @staticmethod
    def find_threshold_for_target_fpr(
        y_true: Sequence[int],
        y_scores: Sequence[float],
        target_fpr: float = 0.01,
    ) -> tuple[float, float, float]:
        """
        Finds the highest threshold tau that guarantees empirical FPR <= target_fpr.
        Returns (optimal_threshold, achieved_fpr, achieved_tpr).
        """
        if len(y_true) != len(y_scores):
            raise ValueError("y_true and y_scores length mismatch")

        fprs, tprs, thresholds = compute_roc_curve(y_true, y_scores)

        # Look for the operating point where FPR <= target_fpr
        # We want the point with maximum TPR subject to FPR <= target_fpr
        best_idx = 0
        for i, (fpr, _) in enumerate(zip(fprs, tprs, strict=False)):
            if fpr <= target_fpr:
                best_idx = i
            else:
                # Since fprs are monotonically increasing, break once exceeded
                break

        optimal_thresh = float(thresholds[best_idx])
        achieved_fpr = float(fprs[best_idx])
        achieved_tpr = float(tprs[best_idx])

        # Clamp threshold to [0.05, 0.99] to prevent degenerate boundary limits
        optimal_thresh = max(0.05, min(0.99, optimal_thresh))

        return optimal_thresh, achieved_fpr, achieved_tpr

    @staticmethod
    def optimize_temperature(
        y_true: Sequence[int],
        y_probs: Sequence[float],
        search_range: tuple[float, float] = (0.2, 5.0),
        steps: int = 50,
    ) -> tuple[float, float, float]:
        """
        Optimizes temperature scalar T using 1D grid search over NLL.
        Scaled logit: z = log(p / (1-p)), p_cal = sigmoid(z / T).
        Returns (best_T, ece_before, ece_after).
        """
        eps = 1e-6
        # Convert probabilities to logits
        logits = [
            math.log(max(eps, min(1.0 - eps, p)) / (1.0 - max(eps, min(1.0 - eps, p))))
            for p in y_probs
        ]

        ece_before = compute_expected_calibration_error(y_true, y_probs)

        best_t = 1.0
        min_nll = float("inf")

        t_min, t_max = search_range
        step_size = (t_max - t_min) / steps

        for step in range(steps + 1):
            t = t_min + step * step_size
            if t <= 0:
                continue

            # Compute NLL under temperature T
            nll = 0.0
            for logit, y in zip(logits, y_true, strict=False):
                # Numerically stable sigmoid: 1 / (1 + exp(-logit / T))
                scaled = logit / t
                if scaled >= 0:
                    prob = 1.0 / (1.0 + math.exp(-scaled))
                else:
                    exp_s = math.exp(scaled)
                    prob = exp_s / (1.0 + exp_s)

                prob = max(eps, min(1.0 - eps, prob))
                if y == 1:
                    nll -= math.log(prob)
                else:
                    nll -= math.log(1.0 - prob)

            if nll < min_nll:
                min_nll = nll
                best_t = t

        # Compute calibrated probs with best_t
        calibrated_probs = []
        for logit in logits:
            scaled = logit / best_t
            if scaled >= 0:
                prob = 1.0 / (1.0 + math.exp(-scaled))
            else:
                exp_s = math.exp(scaled)
                prob = exp_s / (1.0 + exp_s)
            calibrated_probs.append(prob)

        ece_after = compute_expected_calibration_error(y_true, calibrated_probs)

        return round(best_t, 3), round(ece_before, 4), round(ece_after, 4)

    @classmethod
    def calibrate_on_validation_split(
        cls,
        y_true: Sequence[int],
        y_scores: Sequence[float],
        target_fpr: float = 0.01,
    ) -> CalibratedThresholdResult:
        """Runs full calibration pipeline on a validation set."""
        opt_thresh, achieved_fpr, achieved_tpr = cls.find_threshold_for_target_fpr(
            y_true=y_true,
            y_scores=y_scores,
            target_fpr=target_fpr,
        )

        best_t, ece_before, ece_after = cls.optimize_temperature(
            y_true=y_true,
            y_probs=y_scores,
        )

        # Yellow threshold defaults to lower boundary of ambiguous region
        yellow_thresh = max(0.20, round(opt_thresh * 0.55, 3))

        return CalibratedThresholdResult(
            target_fpr=target_fpr,
            achieved_fpr=round(achieved_fpr, 4),
            achieved_tpr=round(achieved_tpr, 4),
            optimal_red_threshold=round(opt_thresh, 3),
            recommended_yellow_threshold=yellow_thresh,
            optimal_temperature=best_t,
            ece_before=ece_before,
            ece_after=ece_after,
            validation_sample_count=len(y_true),
        )
