"""
SafeGate Metric Computation Engine.
Computes empirical, non-faked evaluation metrics for media forensics models:
AUC-ROC, Precision, Recall, F1, FPR at fixed TPR (e.g., FPR@95%TPR),
Expected Calibration Error (ECE), and Brier Score.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationMetrics:
    sample_count: int
    positive_count: int
    negative_count: int
    auc_roc: float
    precision: float
    recall: float
    f1_score: float
    fpr_at_95_tpr: float
    ece: float
    brier_score: float
    threshold_applied: float


def compute_roc_curve(
    y_true: Sequence[int],
    y_scores: Sequence[float],
) -> tuple[list[float], list[float], list[float]]:
    """
    Computes false positive rates (FPR) and true positive rates (TPR)
    across all unique prediction score thresholds sorted descending.
    Returns (fprs, tprs, thresholds).
    """
    if len(y_true) != len(y_scores):
        raise ValueError("y_true and y_scores must have identical length")
    if not y_true:
        return [0.0], [0.0], [0.0]

    total_pos = sum(y_true)
    total_neg = len(y_true) - total_pos

    if total_pos == 0 or total_neg == 0:
        # Trivial single-class degenerate case
        return [0.0, 1.0], [0.0, 1.0], [1.0, 0.0]

    # Sort descending by score
    paired = sorted(zip(y_scores, y_true, strict=False), key=lambda x: x[0], reverse=True)

    tprs = [0.0]
    fprs = [0.0]
    thresholds = [paired[0][0] + 1e-5]

    tp = 0
    fp = 0

    for score, label in paired:
        if label == 1:
            tp += 1
        else:
            fp += 1
        fprs.append(fp / total_neg)
        tprs.append(tp / total_pos)
        thresholds.append(score)

    return fprs, tprs, thresholds


def compute_auc_roc(fprs: Sequence[float], tprs: Sequence[float]) -> float:
    """Computes Area Under the ROC Curve via trapezoidal integration."""
    if len(fprs) != len(tprs) or len(fprs) < 2:
        return 0.5
    auc = 0.0
    for i in range(1, len(fprs)):
        delta_x = fprs[i] - fprs[i - 1]
        avg_y = (tprs[i] + tprs[i - 1]) / 2.0
        auc += delta_x * avg_y
    return max(0.0, min(1.0, float(auc)))


def compute_fpr_at_target_tpr(
    fprs: Sequence[float],
    tprs: Sequence[float],
    target_tpr: float = 0.95,
) -> float:
    """Finds lowest FPR achieved when TPR >= target_tpr."""
    for fpr, tpr in zip(fprs, tprs, strict=False):
        if tpr >= target_tpr:
            return float(fpr)
    return 1.0


def compute_expected_calibration_error(
    y_true: Sequence[int],
    y_probs: Sequence[float],
    n_bins: int = 10,
) -> float:
    """
    Computes Expected Calibration Error (ECE) with equal-width bins.
    ECE = sum_{b=1}^B ( |B_b| / N ) * | acc(B_b) - conf(B_b) |
    """
    n = len(y_true)
    if n == 0:
        return 0.0

    bin_boundaries = [i / n_bins for i in range(n_bins + 1)]
    ece = 0.0

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]

        in_bin_indices = [
            idx
            for idx, p in enumerate(y_probs)
            if (bin_lower <= p < bin_upper) or (i == n_bins - 1 and bin_lower <= p <= bin_upper)
        ]
        bin_size = len(in_bin_indices)
        if bin_size == 0:
            continue

        bin_conf = sum(y_probs[idx] for idx in in_bin_indices) / bin_size
        bin_acc = sum(y_true[idx] for idx in in_bin_indices) / bin_size

        ece += (bin_size / n) * abs(bin_acc - bin_conf)

    return float(ece)


def compute_brier_score(y_true: Sequence[int], y_probs: Sequence[float]) -> float:
    """Computes mean squared calibration error: 1/N * sum((p_i - y_i)^2)."""
    n = len(y_true)
    if n == 0:
        return 0.0
    sq_errs = [(p - y) ** 2 for y, p in zip(y_true, y_probs, strict=False)]
    return float(sum(sq_errs) / n)


def compute_full_evaluation_report(
    y_true: Sequence[int],
    y_scores: Sequence[float],
    decision_threshold: float = 0.5,
) -> EvaluationMetrics:
    """
    Computes comprehensive evaluation metrics on real or benchmark test sets.
    Never invents or scripts metrics; calculated directly from inputs.
    """
    if len(y_true) != len(y_scores):
        raise ValueError("y_true and y_scores must have identical length")

    n = len(y_true)
    positives = sum(y_true)
    negatives = n - positives

    fprs, tprs, _ = compute_roc_curve(y_true, y_scores)
    auc = compute_auc_roc(fprs, tprs)
    fpr_95 = compute_fpr_at_target_tpr(fprs, tprs, target_tpr=0.95)
    ece = compute_expected_calibration_error(y_true, y_scores, n_bins=10)
    brier = compute_brier_score(y_true, y_scores)

    # Classification at decision threshold
    tp = sum(
        1 for y, s in zip(y_true, y_scores, strict=False) if y == 1 and s >= decision_threshold
    )
    fp = sum(
        1 for y, s in zip(y_true, y_scores, strict=False) if y == 0 and s >= decision_threshold
    )
    fn = sum(1 for y, s in zip(y_true, y_scores, strict=False) if y == 1 and s < decision_threshold)

    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return EvaluationMetrics(
        sample_count=n,
        positive_count=positives,
        negative_count=negatives,
        auc_roc=round(auc, 4),
        precision=round(precision, 4),
        recall=round(recall, 4),
        f1_score=round(f1, 4),
        fpr_at_95_tpr=round(fpr_95, 4),
        ece=round(ece, 4),
        brier_score=round(brier, 4),
        threshold_applied=decision_threshold,
    )
