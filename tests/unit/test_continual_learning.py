"""Unit tests for SafeGate continual learning, drift detection, and promotion gating."""

from pathlib import Path

from ml.eval.metrics import EvaluationMetrics
from ml.training.continual_learning import (
    ActiveLearningPool,
    ModelEvaluationGate,
    compute_population_stability_index,
)


def test_active_learning_pool_ingestion(tmp_path: Path) -> None:
    """Verifies edge case selection and deduplication."""
    pool_file = tmp_path / "pool.json"
    pool = ActiveLearningPool(pool_file=pool_file)

    # Edge case 1: High uncertainty
    added1 = pool.ingest_feedback(
        media_sha256="abc123def456",
        frame_index=5,
        model_score=0.45,
        model_uncertainty=0.42,
        human_verdict="ALLOW",
        reviewer_notes="Borderline face lighting",
    )
    assert added1 is True
    assert len(pool.samples) == 1

    # Duplicate should be ignored
    added_dup = pool.ingest_feedback(
        media_sha256="abc123def456",
        frame_index=5,
        model_score=0.45,
        model_uncertainty=0.42,
        human_verdict="ALLOW",
        reviewer_notes="Duplicate attempt",
    )
    assert added_dup is False
    assert len(pool.samples) == 1

    # Confident correct prediction should NOT be ingested
    added_easy = pool.ingest_feedback(
        media_sha256="def789ghi012",
        frame_index=1,
        model_score=0.05,
        model_uncertainty=0.02,
        human_verdict="ALLOW",
        reviewer_notes="Completely authentic video",
    )
    assert added_easy is False
    assert len(pool.samples) == 1


def test_model_promotion_gate() -> None:
    """Gate must reject regressed models and approve models with superior or equal metrics."""
    incumbent = EvaluationMetrics(
        sample_count=100,
        positive_count=50,
        negative_count=50,
        auc_roc=0.920,
        precision=0.90,
        recall=0.88,
        f1_score=0.89,
        fpr_at_95_tpr=0.040,
        ece=0.045,
        brier_score=0.08,
        threshold_applied=0.70,
    )

    # Candidate 1: Better AUC and lower FPR
    candidate_good = EvaluationMetrics(
        sample_count=100,
        positive_count=50,
        negative_count=50,
        auc_roc=0.935,
        precision=0.92,
        recall=0.90,
        f1_score=0.91,
        fpr_at_95_tpr=0.035,
        ece=0.040,
        brier_score=0.07,
        threshold_applied=0.70,
    )
    res_good = ModelEvaluationGate.evaluate_promotion(incumbent, candidate_good)
    assert res_good.approved is True

    # Candidate 2: Severe AUC regression
    candidate_bad = EvaluationMetrics(
        sample_count=100,
        positive_count=50,
        negative_count=50,
        auc_roc=0.890,  # Regressed by 0.030 > 0.005 tolerance
        precision=0.85,
        recall=0.80,
        f1_score=0.82,
        fpr_at_95_tpr=0.070,
        ece=0.050,
        brier_score=0.12,
        threshold_applied=0.70,
    )
    res_bad = ModelEvaluationGate.evaluate_promotion(incumbent, candidate_bad)
    assert res_bad.approved is False
    assert any("Candidate AUC" in r for r in res_bad.reasons)


def test_population_stability_index() -> None:
    """PSI should be low on identical distributions and high on shifted distributions."""
    baseline = [0.1, 0.15, 0.2, 0.25, 0.3, 0.8, 0.85, 0.9]
    similar = [0.11, 0.14, 0.22, 0.24, 0.31, 0.79, 0.86, 0.91]
    psi_stable = compute_population_stability_index(baseline, similar)
    assert psi_stable < 0.15

    # Completely shifted to high values
    shifted = [0.85, 0.88, 0.92, 0.95, 0.97, 0.98, 0.99, 0.99]
    psi_drift = compute_population_stability_index(baseline, shifted)
    assert psi_drift > 0.25
