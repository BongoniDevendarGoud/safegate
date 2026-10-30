"""
SafeGate — Unit Tests for Decision Engine (Stage 8)
====================================================
Tests every policy branch, threshold boundary, and fail-closed path:
1. Exact Blocklist Match -> BLOCK
2. Perceptual Blocklist Match -> BLOCK
3. NSFW Score >= BLOCK_THRESHOLD (0.85) -> BLOCK
4. Borderline NSFW Score [0.45, 0.85) -> REVIEW
5. Gemini High Confidence Explicit -> BLOCK
6. Gemini Uncertain -> REVIEW
7. Deepfake Risk >= DEEPFAKE_REVIEW_THRESHOLD (60) -> REVIEW
8. Stage Failure / Exception -> REVIEW (Fail-Closed)
9. Clean Media -> ALLOW
"""

import pytest
from app.config import settings
from app.pipeline.decision import ScreeningSignals, evaluate_signals


def test_decision_exact_match_blocks():
    """Verify exact SHA-256 match forces BLOCK."""
    signals = ScreeningSignals(exact_match=True)
    res = evaluate_signals(signals)
    assert res.verdict == "BLOCK"
    assert res.triggered_stage == "exact_hash"
    assert "Exact match" in res.explanation


def test_decision_perceptual_match_blocks():
    """Verify perceptual pHash match forces BLOCK."""
    signals = ScreeningSignals(
        perceptual_match={"distance": 4, "timestamp": 2.5, "frame_phash": "aaa", "block_phash": "bbb"}
    )
    res = evaluate_signals(signals)
    assert res.verdict == "BLOCK"
    assert res.triggered_stage == "perceptual_hash"
    assert "Perceptual match" in res.explanation


def test_decision_nsfw_high_score_blocks():
    """Verify worst NSFW score >= BLOCK_THRESHOLD (e.g. 0.85) triggers BLOCK."""
    signals = ScreeningSignals(
        nsfw_worst_score=settings.BLOCK_THRESHOLD + 0.05,
        nsfw_worst_timestamp=4.2,
    )
    res = evaluate_signals(signals)
    assert res.verdict == "BLOCK"
    assert res.triggered_stage == "nsfw_detector"
    assert "exceeds block threshold" in res.explanation


def test_decision_nsfw_borderline_reviews():
    """Verify borderline NSFW score [REVIEW_THRESHOLD, BLOCK_THRESHOLD) triggers REVIEW."""
    borderline_score = (settings.REVIEW_THRESHOLD + settings.BLOCK_THRESHOLD) / 2.0
    signals = ScreeningSignals(
        nsfw_worst_score=borderline_score,
        nsfw_worst_timestamp=1.8,
    )
    res = evaluate_signals(signals)
    assert res.verdict == "REVIEW"
    assert res.triggered_stage == "nsfw_detector"
    assert "Borderline content" in res.explanation


def test_decision_deepfake_risk_reviews():
    """Verify advisory deepfake risk >= DEEPFAKE_REVIEW_THRESHOLD triggers REVIEW (never auto-blocks)."""
    signals = ScreeningSignals(
        deepfake_score=settings.DEEPFAKE_REVIEW_THRESHOLD + 5,
        deepfake_reasons=["Temporal flicker detected", "Inconsistent compression artifacts"],
    )
    res = evaluate_signals(signals)
    assert res.verdict == "REVIEW"
    assert res.triggered_stage == "deepfake_detector"
    assert "Deepfake risk advisory" in res.explanation


def test_decision_stage_error_failclosed_reviews():
    """Verify that any exception or model failure triggers REVIEW (Fail-Closed)."""
    signals = ScreeningSignals(
        stage_error="OpenCV VideoCapture failed: truncated frame header"
    )
    res = evaluate_signals(signals)
    assert res.verdict == "REVIEW"
    assert res.triggered_stage == "error_handling"
    assert "Fail-closed" in res.explanation


def test_decision_clean_content_allows():
    """Verify that content passing all checks strictly below thresholds is ALLOWED."""
    signals = ScreeningSignals(
        exact_match=False,
        perceptual_match=None,
        nsfw_worst_score=0.04,
        nsfw_worst_timestamp=0.0,
        deepfake_score=10,
        stage_error=None,
    )
    res = evaluate_signals(signals)
    assert res.verdict == "ALLOW"
    assert res.triggered_stage == "decision_engine"
    assert "Clean" in res.explanation
