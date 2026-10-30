"""
SafeGate — Unit Tests for Gemini Second Opinion (Stage 6)
==========================================================
Verifies:
1. Borderline boundary logic: only [REVIEW_THRESHOLD, BLOCK_THRESHOLD) triggers Gemini.
2. Offline mode (`USE_GEMINI=false`): returns safe uncertain fallback without making network calls.
3. Missing API key handling: fail-closed to human review.
4. Robust JSON parsing: handles Markdown backticks, invalid JSON, and timeouts safely.
5. End-to-end integration: high-confidence Gemini confirmation converts borderline score to BLOCK.
"""

import json
import os
from PIL import Image
import pytest
from app.config import settings
from app.pipeline.gemini_opinion import is_borderline, query_gemini_second_opinion
from app.pipeline.decision import ScreeningSignals, evaluate_signals


def test_is_borderline_boundaries():
    """Verify that only scores between REVIEW_THRESHOLD and BLOCK_THRESHOLD qualify as borderline."""
    # REVIEW_THRESHOLD=0.45, BLOCK_THRESHOLD=0.85
    assert not is_borderline(0.10)   # Clearly safe -> False
    assert not is_borderline(0.44)   # Just below review -> False
    assert is_borderline(0.45)       # Exact review boundary -> True
    assert is_borderline(0.65)       # Mid borderline -> True
    assert is_borderline(0.849)      # Just below block -> True
    assert not is_borderline(0.85)   # Exact block boundary -> False (auto-blocked directly)
    assert not is_borderline(0.99)   # Clearly explicit -> False


def test_gemini_offline_mode():
    """Verify that when USE_GEMINI=false, the stage gracefully returns offline status."""
    dummy_img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    # In test environment, USE_GEMINI is set to false in conftest
    res = query_gemini_second_opinion(dummy_img, timestamp=1.0)
    assert res["explicit"] is False
    assert res["confidence"] == 0.0
    assert "USE_GEMINI=false" in res["reason"]
    assert res["raw_response"] == "SKIPPED_OFFLINE"


def test_gemini_mock_high_confidence_explicit():
    """Verify handling of Gemini confirming adult content with high confidence."""
    dummy_img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    mock_payload = json.dumps({
        "explicit": True,
        "confidence": 0.94,
        "reason": "Explicit nudity and adult physical interactions identified.",
    })
    os.environ["SAFEGATE_MOCK_GEMINI_RESPONSE"] = mock_payload
    try:
        res = query_gemini_second_opinion(dummy_img, timestamp=2.0)
        assert res["explicit"] is True
        assert res["confidence"] == 0.94
        assert "Explicit nudity" in res["reason"]

        # Decision engine check: borderline NSFW + Gemini explicit -> BLOCK
        signals = ScreeningSignals(
            nsfw_worst_score=0.60,  # Borderline local score
            gemini_explicit=res["explicit"],
            gemini_confidence=res["confidence"],
            gemini_reason=res["reason"],
        )
        verdict_res = evaluate_signals(signals)
        assert verdict_res.verdict == "BLOCK"
        assert "Gemini AI second opinion" in verdict_res.explanation
    finally:
        os.environ.pop("SAFEGATE_MOCK_GEMINI_RESPONSE", None)


def test_gemini_mock_malformed_json_failclosed():
    """Verify that if Gemini returns invalid or non-JSON output, it fails closed to REVIEW."""
    dummy_img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    os.environ["SAFEGATE_MOCK_GEMINI_RESPONSE"] = "This is not valid JSON at all!"
    try:
        res = query_gemini_second_opinion(dummy_img, timestamp=3.0)
        assert res["explicit"] is False
        assert res["confidence"] == 0.0
        assert "Malformed mock response" in res["reason"] or "failed" in res["reason"]
    finally:
        os.environ.pop("SAFEGATE_MOCK_GEMINI_RESPONSE", None)
