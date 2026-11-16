"""
Unit tests for pipeline self-test, score direction mapping, and fail-closed invariants.
"""

from __future__ import annotations

import pytest

from ml.eval.self_test import generate_plumbing_fixture, run_pipeline_self_test
from ml.fusion.calibrator import FusedFrameScores
from ml.fusion.temporal_confirmation import TemporalConfirmationEngine
from safegate_api.config import ThresholdsConfig


def test_score_direction_label_mapping() -> None:
    """
    Step 2e verification: Test score direction and label mapping with known high and low scores.
    High manipulation score (fake=1) -> RED
    Low manipulation score (real=0) -> GREEN
    """
    thresholds = ThresholdsConfig()
    engine = TemporalConfirmationEngine(thresholds=thresholds)

    high_manipulation = FusedFrameScores(
        frame_index=0,
        timestamp_ms=0,
        manipulation_score=0.95,  # Fake = 1
        sensitive_score=0.01,
        uncertainty_score=0.05,
        is_blood_detected=False,
        is_nudity_detected=False,
        branch_contributions={"spatial": 0.95},
        cues={},
    )

    low_manipulation = FusedFrameScores(
        frame_index=0,
        timestamp_ms=0,
        manipulation_score=0.05,  # Real = 0
        sensitive_score=0.01,
        uncertainty_score=0.05,
        is_blood_detected=False,
        is_nudity_detected=False,
        branch_contributions={"spatial": 0.05},
        cues={},
    )

    verdicts_high = engine.evaluate_sequence([high_manipulation])
    assert len(verdicts_high) == 1
    assert verdicts_high[0].color == "RED"
    assert verdicts_high[0].deepfake_score == 0.95

    verdicts_low = engine.evaluate_sequence([low_manipulation])
    assert len(verdicts_low) == 1
    assert verdicts_low[0].color == "GREEN"
    assert verdicts_low[0].deepfake_score == 0.05


def test_startup_self_test_plumbing_passes_in_dev() -> None:
    """Verifies that synthetic plumbing fixtures run cleanly in development mode."""
    from ml.detectors.pipeline import MultiBranchPipeline

    unval_pipe = MultiBranchPipeline(has_validated_model=False, detector_type="heuristic")
    res = run_pipeline_self_test(pipeline=unval_pipe, production_mode=False)
    assert res.passed is True
    assert res.positive_score > res.negative_score
    assert res.production_ready is False  # Because no validated model is loaded
    assert res.details["decision_verdict"] == "HUMAN_REVIEW"
    assert "NO_VALIDATED_MODEL" in res.details["reason"]


def test_startup_self_test_refuses_production_without_validated_model() -> None:
    """Verifies that production mode startup refuses to start without a validated model checkpoint."""
    from ml.detectors.pipeline import MultiBranchPipeline

    unval_pipe = MultiBranchPipeline(has_validated_model=False, detector_type="heuristic")
    with pytest.raises(RuntimeError, match="PRODUCTION GATE REFUSAL"):
        run_pipeline_self_test(pipeline=unval_pipe, production_mode=True)


def test_startup_self_test_passes_production_with_validated_model() -> None:
    """Verifies that production mode startup succeeds when validated model is present."""
    res = run_pipeline_self_test(production_mode=True)
    assert res.passed is True
    assert res.production_ready is True
    assert res.has_validated_model is True
    assert res.detector_type == "model"


def test_plumbing_fixture_generation() -> None:
    """Verifies synthetic plumbing fixtures generate valid dimensions."""
    pos = generate_plumbing_fixture("synthetic_positive")
    neg = generate_plumbing_fixture("synthetic_negative")

    assert pos.shape == (200, 200, 3)
    assert neg.shape == (200, 200, 3)
