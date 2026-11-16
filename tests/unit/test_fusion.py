from ml.detectors.frequency import FrequencyResult
from ml.detectors.pipeline import MultiBranchFrameResult
from ml.detectors.sensitive import SensitiveResult
from ml.detectors.spatial import SpatialResult
from ml.detectors.temporal import TemporalResult
from ml.fusion.calibrator import FusedFrameScores, ScoreCalibrator


def create_mock_raw_result(
    s_spatial: float = 0.1,
    s_freq: float = 0.1,
    s_temp: float = 0.1,
    s_sens: float = 0.05,
    face_detected: bool = False,
    is_first_frame: bool = False,
) -> MultiBranchFrameResult:
    return MultiBranchFrameResult(
        frame_index=0,
        timestamp_ms=0,
        spatial=SpatialResult(
            manipulation_score=s_spatial,
            confidence=0.8,
            face_detected=face_detected,
            face_count=1 if face_detected else 0,
            cues={},
        ),
        frequency=FrequencyResult(
            manipulation_score=s_freq,
            spectral_falloff_slope=-2.1,
            high_freq_ratio=0.03,
            grid_artifact_detected=False,
            cues={},
        ),
        temporal=TemporalResult(
            anomaly_score=s_temp,
            mean_flow_magnitude=1.0,
            flow_variance=2.0,
            is_first_frame=is_first_frame,
            cues={},
        ),
        sensitive=SensitiveResult(
            sensitive_score=s_sens,
            is_blood_detected=False,
            is_nudity_detected=False,
            categories={},
            cues={},
        ),
        cues={},
    )


def test_score_calibrator_clean_inputs() -> None:
    """Verify clean inputs produce low manipulation score and valid uncertainty."""
    calibrator = ScoreCalibrator(temperature=1.25)
    raw = create_mock_raw_result(s_spatial=0.05, s_freq=0.05, s_temp=0.05)

    fused = calibrator.calibrate_and_fuse(raw)
    assert isinstance(fused, FusedFrameScores)
    assert fused.manipulation_score < 0.20
    assert 0.0 <= fused.uncertainty_score <= 1.0
    assert fused.sensitive_score == 0.05


def test_score_calibrator_high_manipulation() -> None:
    """Verify high manipulation across branches produces high fused score."""
    calibrator = ScoreCalibrator(temperature=1.25)
    raw = create_mock_raw_result(s_spatial=0.85, s_freq=0.90, s_temp=0.80, face_detected=True)

    fused = calibrator.calibrate_and_fuse(raw)
    assert fused.manipulation_score > 0.75
    assert fused.branch_contributions["weight_spatial"] == 0.50


def test_score_calibrator_single_frame() -> None:
    """Verify single frame disables temporal branch weight."""
    calibrator = ScoreCalibrator()
    raw = create_mock_raw_result(s_spatial=0.7, s_freq=0.6, s_temp=0.9)

    fused = calibrator.calibrate_and_fuse(raw, is_single_frame=True)
    assert fused.branch_contributions["weight_temporal"] == 0.0
