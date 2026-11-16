from ml.fusion.temporal_confirmation import FrameVerdict
from safegate_worker.policy import ContentPolicyEngine


def make_verdict(idx: int, color: str, deepfake: float = 0.1, sens: float = 0.05) -> FrameVerdict:
    return FrameVerdict(
        frame_index=idx,
        timestamp_ms=idx * 33,
        color=color,
        deepfake_score=deepfake,
        sensitive_score=sens,
        uncertainty_score=0.1,
        confirmation_reason="test",
        cues={},
    )


def test_policy_red_frame_triggers_block() -> None:
    """Verify Priority 1: Any RED frame triggers BLOCK, regardless of other frames."""
    engine = ContentPolicyEngine()
    frames = [
        make_verdict(0, "GREEN"),
        make_verdict(1, "YELLOW"),
        make_verdict(2, "RED", deepfake=0.91),
        make_verdict(3, "GREEN"),
    ]

    decision = engine.evaluate(frames)
    assert decision.verdict == "BLOCK"
    assert decision.red_frames == 1
    assert decision.red_frame_indices == [2]
    assert len(decision.suspicious_intervals) == 1
    assert decision.suspicious_intervals[0].start_frame == 2


def test_policy_yellow_triggers_human_review() -> None:
    """Verify Priority 2: Any YELLOW frame (with no RED) triggers HUMAN_REVIEW."""
    engine = ContentPolicyEngine()
    frames = [
        make_verdict(0, "GREEN"),
        make_verdict(1, "YELLOW", sens=0.65),
        make_verdict(2, "GREEN"),
    ]

    decision = engine.evaluate(frames)
    assert decision.verdict == "HUMAN_REVIEW"
    assert decision.yellow_frames == 1
    assert decision.red_frames == 0
    assert decision.yellow_frame_indices == [1]


def test_policy_all_green_triggers_allow() -> None:
    """Verify Priority 3: 100% GREEN frames triggers ALLOW."""
    engine = ContentPolicyEngine()
    frames = [
        make_verdict(0, "GREEN"),
        make_verdict(1, "GREEN"),
        make_verdict(2, "GREEN"),
    ]

    decision = engine.evaluate(frames)
    assert decision.verdict == "ALLOW"
    assert decision.total_frames == 3
    assert decision.green_frames == 3
    assert decision.red_frames == 0
    assert decision.yellow_frames == 0


def test_policy_fail_closed_on_empty_frames() -> None:
    """Verify fail-closed invariant: 0 frames never returns ALLOW."""
    engine = ContentPolicyEngine()
    decision = engine.evaluate([])
    assert decision.verdict == "HUMAN_REVIEW"
    assert decision.metadata["fail_closed"] is True


def test_policy_fail_closed_on_error_flag() -> None:
    """Verify fail-closed invariant: error flag forces HUMAN_REVIEW."""
    engine = ContentPolicyEngine()
    frames = [make_verdict(0, "GREEN"), make_verdict(1, "GREEN")]

    decision = engine.evaluate(frames, fail_closed_triggered=True, error_context="Timeout")
    assert decision.verdict == "HUMAN_REVIEW"
    assert "Timeout" in decision.summary_reason
