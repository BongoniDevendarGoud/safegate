"""
SafeGate Startup Self-Test & Production Gate.
Executes synthetic positive and negative plumbing test fixtures on pipeline initialization.
Guarantees fail-closed startup: refuses to start in production mode if a validated model is missing
or if pipeline plumbing fails to separate positive and negative test fixtures.

NOTE: These fixtures are strictly plumbing sanity checks, NOT accuracy or generalization benchmarks.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from ml.detectors.pipeline import MultiBranchPipeline
from ml.fusion.calibrator import ScoreCalibrator
from ml.fusion.temporal_confirmation import TemporalConfirmationEngine
from safegate_api.config import settings
from safegate_worker.policy import ContentPolicyEngine


@dataclass(frozen=True)
class SelfTestResult:
    passed: bool
    production_ready: bool
    positive_score: float
    negative_score: float
    detector_type: str
    has_validated_model: bool
    summary: str
    details: dict[str, Any]


def generate_plumbing_fixture(kind: str) -> np.ndarray:
    """
    Generates synthetic in-memory fixtures for pipeline plumbing verification.
    NOTICE: Strictly a pipeline integrity test; not evidence of empirical deepfake detection accuracy.
    """
    img = np.zeros((200, 200, 3), dtype=np.uint8)

    if kind == "synthetic_positive":
        # Synthetic checkerboard with alternating color channels to trigger frequency grid & boundary anomalies
        for y in range(0, 200, 8):
            for x in range(0, 200, 8):
                if ((x + y) // 8) % 2 == 0:
                    img[y : y + 8, x : x + 8] = [255, 20, 20]
                else:
                    img[y : y + 8, x : x + 8] = [20, 255, 255]
    elif kind == "synthetic_negative":
        # Uniform smooth gradient simulating continuous sensor noise without grid artifacts
        for y in range(200):
            val = int(100 + 50 * (y / 200.0))
            img[y, :] = [val, val, val]
    else:
        raise ValueError(f"Unknown plumbing fixture kind: {kind}")

    return img


def run_pipeline_self_test(
    pipeline: MultiBranchPipeline | None = None,
    production_mode: bool = False,
) -> SelfTestResult:
    """
    Runs plumbing self-test across synthetic positive and negative fixtures.
    In production mode, enforces that a validated model is present and capable of separation.
    """
    pipe = pipeline or MultiBranchPipeline()
    calibrator = ScoreCalibrator()
    confirmation_engine = TemporalConfirmationEngine(thresholds=settings.thresholds)
    policy_engine = ContentPolicyEngine()

    pipe.reset()

    # 1. Generate fixtures with explicit labeling
    # [PLUMBING_TEST: Not an accuracy benchmark or generalization evidence]
    pos_frame = generate_plumbing_fixture("synthetic_positive")
    neg_frame = generate_plumbing_fixture("synthetic_negative")

    # 2. Run positive fixture
    raw_pos = pipe.process_frame(pos_frame, frame_index=0, timestamp_ms=0)
    fused_pos = calibrator.calibrate_and_fuse(raw_pos, is_single_frame=True)

    # 3. Run negative fixture
    raw_neg = pipe.process_frame(neg_frame, frame_index=1, timestamp_ms=33)
    fused_neg = calibrator.calibrate_and_fuse(raw_neg, is_single_frame=True)

    # 4. Check for numerical validity
    scores = [
        fused_pos.manipulation_score,
        fused_pos.sensitive_score,
        fused_pos.uncertainty_score,
        fused_neg.manipulation_score,
        fused_neg.sensitive_score,
        fused_neg.uncertainty_score,
    ]
    if any(math.isnan(s) or math.isinf(s) for s in scores):
        return SelfTestResult(
            passed=False,
            production_ready=False,
            positive_score=fused_pos.manipulation_score,
            negative_score=fused_neg.manipulation_score,
            detector_type=pipe.detector_type,
            has_validated_model=pipe.has_validated_model,
            summary="FAIL: Numerical instability (NaN/Inf) detected in pipeline plumbing output.",
            details={"scores": scores},
        )

    # 5. Check separation on plumbing fixtures
    separated = fused_pos.manipulation_score > fused_neg.manipulation_score
    if not separated:
        return SelfTestResult(
            passed=False,
            production_ready=False,
            positive_score=fused_pos.manipulation_score,
            negative_score=fused_neg.manipulation_score,
            detector_type=pipe.detector_type,
            has_validated_model=pipe.has_validated_model,
            summary=(
                f"FAIL: Pipeline plumbing failed to separate synthetic positive ({fused_pos.manipulation_score:.4f}) "
                f"from negative ({fused_neg.manipulation_score:.4f})."
            ),
            details={"pos_cues": raw_pos.cues, "neg_cues": raw_neg.cues},
        )

    # 6. Verify policy engine fail-closed enforcement
    verdicts = confirmation_engine.evaluate_sequence([fused_neg])
    decision = policy_engine.evaluate(
        frame_verdicts=verdicts,
        detector_type=pipe.detector_type,
        has_validated_model=pipe.has_validated_model,
        has_calibrated_thresholds=pipe.has_calibrated_thresholds,
    )

    # Without a validated model, verdict must NEVER be ALLOW
    if not pipe.has_validated_model and decision.verdict == "ALLOW":
        return SelfTestResult(
            passed=False,
            production_ready=False,
            positive_score=fused_pos.manipulation_score,
            negative_score=fused_neg.manipulation_score,
            detector_type=pipe.detector_type,
            has_validated_model=pipe.has_validated_model,
            summary="CRITICAL FAIL: System returned ALLOW without a validated model loaded (fail-open violation).",
            details={"verdict": decision.verdict},
        )

    # 7. Production mode gate
    production_ready = pipe.detector_type == "model" and pipe.has_validated_model
    if production_mode and not production_ready:
        raise RuntimeError(
            "PRODUCTION GATE REFUSAL: Production mode requires a validated, trained neural network model. "
            f"Current detector_type is '{pipe.detector_type}' with has_validated_model=False. Refusing to start."
        )

    return SelfTestResult(
        passed=True,
        production_ready=production_ready,
        positive_score=fused_pos.manipulation_score,
        negative_score=fused_neg.manipulation_score,
        detector_type=pipe.detector_type,
        has_validated_model=pipe.has_validated_model,
        summary=(
            f"PASSED [PLUMBING_TEST: Not an accuracy benchmark]. Positive score: {fused_pos.manipulation_score:.4f}, "
            f"Negative score: {fused_neg.manipulation_score:.4f}. Production ready: {production_ready}."
        ),
        details={"decision_verdict": decision.verdict, "reason": decision.summary_reason},
    )
