from pathlib import Path

import cv2
import numpy as np
import pytest

from safegate_api.errors import MediaDecodeError
from safegate_worker.extractor import (
    FrameData,
    extract_media_frames,
    extract_still_image,
    stream_video_frames,
)


def create_synthetic_image(path: Path, width: int = 160, height: int = 120) -> None:
    """Helper creating a valid test image file."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:, :] = (100, 150, 200)
    cv2.imwrite(str(path), img)


def create_synthetic_video(
    path: Path, frames: int = 5, width: int = 160, height: int = 120
) -> None:
    """Helper creating a small valid MP4 test video."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore[attr-defined]
    out = cv2.VideoWriter(str(path), fourcc, 30.0, (width, height))
    for i in range(frames):
        frame = np.full((height, width, 3), fill_value=i * 40, dtype=np.uint8)
        out.write(frame)
    out.release()


def test_extract_still_image(tmp_path: Path) -> None:
    """Verify single frame extraction from image file."""
    img_path = tmp_path / "test.jpg"
    create_synthetic_image(img_path)

    frame = extract_still_image(img_path)
    assert isinstance(frame, FrameData)
    assert frame.frame_index == 0
    assert frame.timestamp_ms == 0
    assert frame.width == 160
    assert frame.height == 120
    assert len(frame.sha256_hash) == 64


def test_stream_video_frames(tmp_path: Path) -> None:
    """Verify streaming generator yields each frame sequentially with hashes."""
    vid_path = tmp_path / "test.mp4"
    create_synthetic_video(vid_path, frames=5)

    frames = list(stream_video_frames(vid_path))
    assert len(frames) == 5

    for idx, frame in enumerate(frames):
        assert frame.frame_index == idx
        assert frame.width == 160
        assert frame.height == 120
        assert len(frame.sha256_hash) == 64
        if idx > 0:
            assert frame.sha256_hash != frames[idx - 1].sha256_hash


def test_extract_media_frames_routes_image_and_video(tmp_path: Path) -> None:
    """Verify unified extract_media_frames handles both images and videos."""
    img_path = tmp_path / "photo.png"
    create_synthetic_image(img_path)
    img_frames = list(extract_media_frames(img_path))
    assert len(img_frames) == 1

    vid_path = tmp_path / "clip.mp4"
    create_synthetic_video(vid_path, frames=3)
    vid_frames = list(extract_media_frames(vid_path))
    assert len(vid_frames) == 3


def test_extractor_handles_corrupt_file(tmp_path: Path) -> None:
    """Verify corrupted video file raises MediaDecodeError."""
    corrupt_file = tmp_path / "bad.mp4"
    corrupt_file.write_bytes(b"\x00" * 50)

    with pytest.raises(MediaDecodeError):
        list(stream_video_frames(corrupt_file))
