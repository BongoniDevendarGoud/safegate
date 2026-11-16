from ml.fusion.calibrator import FusedFrameScores
from ml.fusion.temporal_confirmation import TemporalConfirmationEngine


def make_fused_frame(
    idx: int,
    ts: int,
    manip: float = 0.1,
    sens: float = 0.05,
    uncert: float = 0.1,
    blood: bool = False,
    nudity: bool = False,
) -> FusedFrameScores:
    return FusedFrameScores(
        frame_index=idx,
        timestamp_ms=ts,
        manipulation_score=manip,
        sensitive_score=sens,
        uncertainty_score=uncert,
        is_blood_detected=blood,
        is_nudity_detected=nudity,
        branch_contributions={},
        cues={},
    )


def test_temporal_confirmation_downgrades_isolated_spike() -> None:
    """Verify Rule 7: Isolated single candidate RED frame surrounded by green is downgraded to YELLOW."""
    engine = TemporalConfirmationEngine(min_consecutive_red=2)

    # 5 frames: [Green, Green, Candidate RED, Green, Green]
    frames = [
        make_fused_frame(0, 0, manip=0.10),
        make_fused_frame(1, 33, manip=0.12),
        make_fused_frame(2, 66, manip=0.82),  # Spike >= 0.78
        make_fused_frame(3, 99, manip=0.10),
        make_fused_frame(4, 132, manip=0.15),
    ]

    verdicts = engine.evaluate_sequence(frames)
    assert len(verdicts) == 5

    # Frame 2 must be downgraded to YELLOW (not RED)
    assert verdicts[0].color == "GREEN"
    assert verdicts[1].color == "GREEN"
    assert verdicts[2].color == "YELLOW"
    assert "downgraded to YELLOW" in verdicts[2].confirmation_reason
    assert verdicts[3].color == "GREEN"
    assert verdicts[4].color == "GREEN"


def test_temporal_confirmation_confirms_consecutive_red() -> None:
    """Verify that 2+ consecutive high-manipulation frames are confirmed as RED."""
    engine = TemporalConfirmationEngine(min_consecutive_red=2)

    # Consecutive RED frames at indices 2 and 3
    frames = [
        make_fused_frame(0, 0, manip=0.10),
        make_fused_frame(1, 33, manip=0.12),
        make_fused_frame(2, 66, manip=0.85),
        make_fused_frame(3, 99, manip=0.88),
        make_fused_frame(4, 132, manip=0.15),
    ]

    verdicts = engine.evaluate_sequence(frames)
    assert verdicts[2].color == "RED"
    assert verdicts[3].color == "RED"
    assert "RED confirmed" in verdicts[2].confirmation_reason


def test_temporal_confirmation_sensitive_assignment() -> None:
    """Verify that blood/nudity assigns YELLOW color without manipulation."""
    engine = TemporalConfirmationEngine()

    frames = [
        make_fused_frame(0, 0, manip=0.05, sens=0.75, blood=True),
    ]

    verdicts = engine.evaluate_sequence(frames)
    assert verdicts[0].color == "YELLOW"
    assert "blood/violence" in verdicts[0].confirmation_reason
