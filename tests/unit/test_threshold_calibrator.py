"""Unit tests for SafeGate threshold calibrator and temperature scaling."""

from ml.eval.thresholds import CalibratedThresholdResult, ThresholdCalibrator


def test_find_threshold_for_target_fpr() -> None:
    """Ensure discovered threshold achieves requested false positive rate constraint."""
    # 20 negatives, 20 positives
    y_true = [0] * 20 + [1] * 20
    # Negatives have lower scores; positives have higher scores
    y_scores = [0.05 + 0.02 * i for i in range(20)] + [0.60 + 0.015 * i for i in range(20)]

    # Target FPR <= 0.05 (at most 1 false positive out of 20)
    thresh, ach_fpr, ach_tpr = ThresholdCalibrator.find_threshold_for_target_fpr(
        y_true=y_true,
        y_scores=y_scores,
        target_fpr=0.05,
    )

    assert ach_fpr <= 0.05
    assert ach_tpr >= 0.95
    assert 0.05 <= thresh <= 0.99


def test_temperature_optimization() -> None:
    """Ensure temperature scaling can be fit and does not blow up ECE."""
    y_true = [0, 0, 0, 0, 1, 1, 1, 1]
    y_probs = [0.15, 0.20, 0.10, 0.25, 0.85, 0.80, 0.90, 0.75]

    best_t, ece_before, ece_after = ThresholdCalibrator.optimize_temperature(
        y_true=y_true,
        y_probs=y_probs,
        steps=20,
    )

    assert best_t > 0
    assert ece_after <= ece_before + 0.05


def test_calibrate_on_validation_split() -> None:
    """End-to-end threshold and temperature calibration test."""
    y_true = [0] * 15 + [1] * 15
    y_scores = [0.1] * 14 + [0.55] + [0.85] * 15

    res = ThresholdCalibrator.calibrate_on_validation_split(
        y_true=y_true,
        y_scores=y_scores,
        target_fpr=0.10,
    )

    assert isinstance(res, CalibratedThresholdResult)
    assert res.achieved_fpr <= 0.10
    assert res.optimal_red_threshold > res.recommended_yellow_threshold
    assert res.validation_sample_count == 30
