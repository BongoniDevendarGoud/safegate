"""
SafeGate — Unit Tests for Deepfake Heuristics (Stage 7)
========================================================
Verifies:
1. Temporal flicker detection on fluctuating frame sequences.
2. Compression residual analysis.
3. Metadata inspection for re-encoding and camera signatures.
4. Composite score calculation (bounded between 0 and 100).
5. Advisory nature: high score routes to REVIEW, NEVER auto-blocks.
"""

from pathlib import Path
import tempfile
import numpy as np
from PIL import Image, ImageDraw
import pytest
from app.config import settings
from app.pipeline.deepfake_detector import (
    evaluate_temporal_flicker,
    evaluate_compression_artifacts,
    evaluate_container_metadata,
    calculate_deepfake_risk,
)
from app.pipeline.decision import ScreeningSignals, evaluate_signals


def test_temporal_flicker_detection():
    """Verify that severe alternating color flicker between frames is flagged."""
    # Sequence of 4 frames alternating violently between white and black
    f1 = Image.new("RGB", (100, 100), color=(255, 255, 255))
    f2 = Image.new("RGB", (100, 100), color=(0, 0, 0))
    f3 = Image.new("RGB", (100, 100), color=(255, 255, 255))
    f4 = Image.new("RGB", (100, 100), color=(0, 0, 0))

    frames = [(0.0, f1), (0.5, f2), (1.0, f3), (1.5, f4)]
    score, reasons = evaluate_temporal_flicker(frames)

    assert score > 0
    assert len(reasons) > 0
    assert any("flicker" in r.lower() or "discontinuity" in r.lower() for r in reasons)


def test_compression_artifacts_evaluation():
    """Verify compression artifact analysis runs and bounds scores safely."""
    # Create smooth gradient frame
    img = Image.new("RGB", (100, 100), color=(128, 128, 128))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 80, 80], fill=(200, 50, 50))

    frames = [(0.0, img), (1.0, img)]
    score, reasons = evaluate_compression_artifacts(frames)
    assert 0 <= score <= 25


def test_container_metadata_inspection():
    """Verify container header analysis flags suspicious transcoder signatures."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        # Simulate video header with Lavf (FFmpeg) tag
        tmp.write(b"ftypmp42" + b"\x00" * 100 + b"Lavf60.16.100" + b"\x00" * 100)
        tmp_path = Path(tmp.name)

    try:
        score, reasons = evaluate_container_metadata(tmp_path)
        assert score > 0
        assert any("Lavf" in r for r in reasons)
    finally:
        tmp_path.unlink()


def test_composite_deepfake_risk_bounds_and_advisory_rule(generate_synthetic_video):
    """
    Verify full composite risk score:
    - Bounded between 0 and 100.
    - Advisory rule: A high score (e.g. 75) forces REVIEW, NEVER auto-blocks.
    """
    video_path, _ = generate_synthetic_video(duration_sec=2)

    f1 = Image.new("RGB", (100, 100), color=(200, 200, 200))
    f2 = Image.new("RGB", (100, 100), color=(10, 10, 10))
    frames = [(0.0, f1), (1.0, f2)]

    score, reasons = calculate_deepfake_risk(video_path, frames)
    assert 0 <= score <= 100

    # Test Decision Engine with simulated high deepfake score
    signals = ScreeningSignals(
        deepfake_score=85,
        deepfake_reasons=["Temporal flicker detected", "Lavf synthetic encoder signature"],
    )
    decision = evaluate_signals(signals)

    # CRITICAL ADVISORY RULE CHECK
    assert decision.verdict == "REVIEW", "High deepfake score must trigger REVIEW, NEVER auto-BLOCK"
    assert "Deepfake risk advisory" in decision.explanation
