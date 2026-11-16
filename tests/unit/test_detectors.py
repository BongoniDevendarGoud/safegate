import numpy as np

from ml.detectors.frequency import FrequencyDetector
from ml.detectors.pipeline import MultiBranchPipeline
from ml.detectors.sensitive import SensitiveContentClassifier
from ml.detectors.spatial import SpatialDetector
from ml.detectors.temporal import TemporalDetector


def test_spatial_detector_fallback_mode() -> None:
    """Verify spatial detector handles image without detected faces using whole-image fallback."""
    detector = SpatialDetector()
    # Plain smooth gradient image (no faces)
    img = np.zeros((120, 160, 3), dtype=np.uint8)
    for i in range(160):
        img[:, i] = (i % 256, (i * 2) % 256, (i * 3) % 256)

    result = detector.analyze_frame(img)
    assert not result.face_detected
    assert result.face_count == 0
    assert 0.0 <= result.manipulation_score <= 1.0
    assert result.confidence == 0.60
    assert "overall_sharpness" in result.cues


def test_frequency_detector_radial_analysis() -> None:
    """Verify 2D FFT frequency detector extracts slope and high-frequency metrics."""
    detector = FrequencyDetector()

    # Synthetic checkerboard pattern with sharp periodic frequencies
    img = np.zeros((256, 256, 3), dtype=np.uint8)
    img[::8, ::8] = 255
    img[1::8, 1::8] = 255

    result = detector.analyze_frame(img)
    assert 0.0 <= result.manipulation_score <= 1.0
    assert isinstance(result.spectral_falloff_slope, float)
    assert isinstance(result.grid_artifact_detected, bool)
    assert "slope" in result.cues


def test_temporal_detector_sequence() -> None:
    """Verify temporal detector tracking across consecutive frames."""
    detector = TemporalDetector()

    frame1 = np.full((120, 160, 3), 100, dtype=np.uint8)
    frame2 = np.full((120, 160, 3), 180, dtype=np.uint8)

    # First frame should have 0 anomaly
    res1 = detector.analyze_frame(frame1)
    assert res1.is_first_frame is True
    assert res1.anomaly_score == 0.0

    # Second frame with motion/illumination shift
    res2 = detector.analyze_frame(frame2)
    assert res2.is_first_frame is False
    assert 0.0 <= res2.anomaly_score <= 1.0


def test_sensitive_classifier_clean_image() -> None:
    """Verify clean image produces low sensitive score."""
    classifier = SensitiveContentClassifier()
    # Green forest / blue sky landscape
    img = np.zeros((120, 160, 3), dtype=np.uint8)
    img[:60, :] = [135, 206, 235]  # Sky blue (RGB)
    img[60:, :] = [34, 139, 34]  # Forest green (RGB)

    result = classifier.analyze_frame(img)
    assert result.sensitive_score < 0.20
    assert not result.is_blood_detected
    assert not result.is_nudity_detected


def test_sensitive_classifier_blood_detection() -> None:
    """Verify synthetic blood-colored region triggers blood detection."""
    classifier = SensitiveContentClassifier()
    # Image with substantial crimson / blood red pool in center
    img = np.full((120, 160, 3), fill_value=200, dtype=np.uint8)
    # Crimson red in RGB: high red, low green/blue
    img[30:90, 40:120] = [180, 10, 20]

    result = classifier.analyze_frame(img)
    assert result.is_blood_detected is True
    assert result.sensitive_score >= 0.45
    assert result.categories["blood_violence"] >= 0.45


def test_multibranch_pipeline_orchestration() -> None:
    """Verify unified pipeline orchestrator runs all 4 branches."""
    pipeline = MultiBranchPipeline()
    img = np.full((120, 160, 3), fill_value=128, dtype=np.uint8)

    frame_res = pipeline.process_frame(img, frame_index=1, timestamp_ms=33)
    assert frame_res.frame_index == 1
    assert frame_res.timestamp_ms == 33
    assert frame_res.spatial is not None
    assert frame_res.frequency is not None
    assert frame_res.temporal is not None
    assert frame_res.sensitive is not None
    assert "spatial" in frame_res.cues
    assert "sensitive" in frame_res.cues
