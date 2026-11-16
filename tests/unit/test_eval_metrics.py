"""Unit tests for SafeGate evaluation metric computation."""

from ml.eval.metrics import (
    compute_auc_roc,
    compute_brier_score,
    compute_expected_calibration_error,
    compute_fpr_at_target_tpr,
    compute_full_evaluation_report,
    compute_roc_curve,
)


def test_roc_and_auc_perfect_classifier() -> None:
    """Perfect classifier where all positives score 1.0 and negatives score 0.0."""
    y_true = [0, 0, 0, 1, 1, 1]
    y_scores = [0.1, 0.2, 0.15, 0.85, 0.9, 0.95]

    fprs, tprs, thresholds = compute_roc_curve(y_true, y_scores)
    assert len(fprs) == len(tprs) == len(thresholds)
    auc = compute_auc_roc(fprs, tprs)
    assert auc == 1.0

    fpr_95 = compute_fpr_at_target_tpr(fprs, tprs, target_tpr=0.95)
    assert fpr_95 == 0.0


def test_roc_and_auc_random_or_inverted() -> None:
    """Inverted scores should yield low AUC."""
    y_true = [0, 0, 1, 1]
    y_scores = [0.9, 0.8, 0.1, 0.2]

    fprs, tprs, _ = compute_roc_curve(y_true, y_scores)
    auc = compute_auc_roc(fprs, tprs)
    assert auc == 0.0


def test_expected_calibration_error() -> None:
    """Calibrated predictions should have very low ECE."""
    # Well-calibrated: ~80% positive predictions have ~0.8 true labels
    y_true = [1, 1, 1, 1, 0, 0, 0, 0, 0, 0]
    y_probs = [0.8, 0.8, 0.8, 0.8, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1]

    ece = compute_expected_calibration_error(y_true, y_probs, n_bins=10)
    assert 0.0 <= ece < 0.25

    # Poorly calibrated: all predicted 0.99 but true labels are all 0
    y_true_bad = [0, 0, 0, 0]
    y_probs_bad = [0.99, 0.99, 0.99, 0.99]
    ece_bad = compute_expected_calibration_error(y_true_bad, y_probs_bad, n_bins=10)
    assert ece_bad > 0.90


def test_brier_score() -> None:
    """Brier score should equal MSE of predicted probabilities vs binary ground truth."""
    y_true = [1, 0]
    y_probs = [0.9, 0.2]
    # (0.9 - 1)^2 = 0.01; (0.2 - 0)^2 = 0.04; mean = 0.025
    brier = compute_brier_score(y_true, y_probs)
    assert abs(brier - 0.025) < 1e-4


def test_full_evaluation_report() -> None:
    """Verifies complete evaluation report generation."""
    y_true = [0, 0, 0, 1, 1, 1]
    y_scores = [0.05, 0.12, 0.25, 0.78, 0.89, 0.95]

    report = compute_full_evaluation_report(y_true, y_scores, decision_threshold=0.5)
    assert report.sample_count == 6
    assert report.positive_count == 3
    assert report.negative_count == 3
    assert report.auc_roc == 1.0
    assert report.precision == 1.0
    assert report.recall == 1.0
    assert report.f1_score == 1.0
    assert report.threshold_applied == 0.5
