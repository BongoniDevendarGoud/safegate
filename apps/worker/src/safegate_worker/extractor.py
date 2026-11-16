"""
SafeGate Streaming Frame Extractor.
Extracts every frame of a video or single-frame image without loading full media into memory.
Enforces decoding resource limits and computes per-frame SHA-256 hashes.
"""

from __future__ import annotations

import hashlib
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from safegate_api.errors import MediaDecodeError

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@dataclass(frozen=True)
class FrameData:
    frame_index: int
    timestamp_ms: int
    rgb_array: np.ndarray
    sha256_hash: str
    width: int
    height: int


def compute_frame_hash(rgb_frame: np.ndarray) -> str:
    """Computes SHA-256 digest of raw uncompressed RGB pixel buffer."""
    return hashlib.sha256(rgb_frame.tobytes()).hexdigest()


def extract_still_image(image_path: Path) -> FrameData:
    """Extracts a single frame from an image file."""
    bgr_img = cv2.imread(str(image_path))
    if bgr_img is None:
        raise MediaDecodeError(f"Failed to decode image file: {image_path.name}")

    rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
    h, w = rgb_img.shape[:2]
    frame_hash = compute_frame_hash(rgb_img)

    return FrameData(
        frame_index=0,
        timestamp_ms=0,
        rgb_array=rgb_img,
        sha256_hash=frame_hash,
        width=w,
        height=h,
    )


def stream_video_frames(
    video_path: Path,
    max_frames: int = 18000,  # Max 10 mins @ 30fps
    max_dimension: int = 3840,  # Max 4K resolution
) -> Generator[FrameData, None, None]:
    """
    Streaming generator that yields one decoded frame at a time.
    Guards against decompression bombs, memory exhaustion, and invalid PTS.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise MediaDecodeError(f"Unable to open video container: {video_path.name}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or np.isnan(fps):
        fps = 30.0  # Fallback assumption for variable framerate

    frame_index = 0

    try:
        while True:
            ret, bgr_frame = cap.read()
            if not ret or bgr_frame is None:
                break

            h, w = bgr_frame.shape[:2]
            if h > max_dimension or w > max_dimension:
                raise MediaDecodeError(
                    f"Frame dimension {w}x{h} exceeds allowed maximum ({max_dimension}px)."
                )

            if frame_index >= max_frames:
                raise MediaDecodeError(
                    f"Video exceeds maximum allowed frame limit ({max_frames} frames)."
                )

            # Get timestamp in milliseconds
            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            if timestamp_ms <= 0 and frame_index > 0:
                timestamp_ms = int((frame_index / fps) * 1000)

            rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
            frame_hash = compute_frame_hash(rgb_frame)

            yield FrameData(
                frame_index=frame_index,
                timestamp_ms=timestamp_ms,
                rgb_array=rgb_frame,
                sha256_hash=frame_hash,
                width=w,
                height=h,
            )

            frame_index += 1

        if frame_index == 0:
            raise MediaDecodeError("Video stream contains 0 decodable frames.")

    finally:
        cap.release()


def extract_media_frames(
    media_path: Path,
    max_frames: int = 18000,
) -> Generator[FrameData, None, None]:
    """
    Unified entry point for media frame extraction.
    Automatically routes still images to single-frame extractor and videos to streaming decoder.
    """
    if not media_path.exists():
        raise FileNotFoundError(f"Media file not found: {media_path}")

    suffix = media_path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        yield extract_still_image(media_path)
    else:
        yield from stream_video_frames(media_path, max_frames=max_frames)
