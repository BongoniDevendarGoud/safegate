"""
SafeGate — Unit Tests for Frame Extraction (Stage 3)
=====================================================
Verifies:
1. Video frame extraction with OpenCV.
2. Temporal distribution (first frame, interval step, last frame).
3. Frame resizing to configured dimensions (640, 480).
4. Safety cap on maximum extracted frames (MAX_FRAMES).
5. Fail-closed behavior on corrupted or unreadable video streams.
"""

from pathlib import Path
import tempfile
import pytest
from app.pipeline.frame_extraction import extract_video_frames


def test_frame_extraction_temporal_sampling(generate_synthetic_video):
    """
    Verify that a 4-second video sampled at 2-second intervals
    extracts first frame (0.0s), 2.0s, and last frame (~3.9s).
    """
    video_path, _ = generate_synthetic_video(duration_sec=4, fps=10)
    frames = extract_video_frames(
        video_path=video_path,
        interval_sec=2,
        max_frames=60,
        resize_dims=(320, 240),
    )

    assert len(frames) >= 3
    # Check first frame timestamp is 0.0s
    first_ts, first_img = frames[0]
    assert first_ts == 0.0
    assert first_img.size == (320, 240)

    # Check last frame timestamp is near 3.9s
    last_ts, last_img = frames[-1]
    assert last_ts >= 3.0
    assert last_img.size == (320, 240)


def test_frame_extraction_max_frames_cap(generate_synthetic_video):
    """
    Verify that if a video would yield more frames than max_frames,
    it is strictly capped to prevent CPU/memory exhaustion.
    """
    # 6-second video with interval_sec=1 -> would generate ~7 frames
    video_path, _ = generate_synthetic_video(duration_sec=6, fps=10)
    capped_frames = extract_video_frames(
        video_path=video_path,
        interval_sec=1,
        max_frames=3,
        resize_dims=(160, 120),
    )
    assert len(capped_frames) <= 3


def test_frame_extraction_corrupted_file_failclosed():
    """
    Verify that an unreadable or truncated file raises ValueError,
    ensuring it fails closed to REVIEW rather than passing through.
    """
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(b"CORRUPTED_VIDEO_HEADER_AND_GARBAGE_PAYLOAD")
        bad_path = Path(tmp.name)

    try:
        with pytest.raises(ValueError, match="Corrupted or unsupported video stream|No readable visual frames"):
            extract_video_frames(bad_path)
    finally:
        bad_path.unlink()
