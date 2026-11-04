"""
SafeGate — Frame Extraction Module (Pipeline Stage 3)
======================================================
Extracts representative visual frames from quarantined videos using OpenCV:

ALGORITHM:
1. Opens video using `cv2.VideoCapture`.
2. Computes total frame count, FPS, and duration in seconds.
3. Targets:
   - First frame (0.0 seconds)
   - Every N seconds based on FRAME_INTERVAL_SEC (default 2 seconds)
   - Last available frame
4. Capped at MAX_FRAMES (default 60) to prevent CPU/memory denial-of-service.
5. Normalization: Resizes each extracted frame to (640, 480) and converts
   OpenCV's native BGR color channel format to RGB for PIL / model compatibility.

FAIL-CLOSED BEHAVIOR:
If OpenCV fails to open the video file or cannot decode valid frames,
a ValueError is raised so the orchestrator routes the file to REVIEW.
"""

import logging
from pathlib import Path
from typing import List, Tuple
import cv2
import numpy as np
from PIL import Image
from app.config import settings

logger = logging.getLogger(__name__)


def extract_video_frames(
    video_path: Path,
    interval_sec: int = None,
    max_frames: int = None,
    resize_dims: Tuple[int, int] = None,
) -> List[Tuple[float, Image.Image]]:
    """
    Extracts temporally distributed frames from a video file on disk.

    Args:
        video_path: Path to the video in quarantine.
        interval_sec: Step size between frames in seconds (default: settings.FRAME_INTERVAL_SEC).
        max_frames: Maximum number of frames returned (default: settings.MAX_FRAMES).
        resize_dims: (width, height) to resize frames to (default: settings.FRAME_RESIZE).

    Returns:
        List of (timestamp_in_seconds, PIL.Image) tuples.

    Raises:
        ValueError: If the video cannot be opened, has 0 frames, or decoding fails.
    """
    if interval_sec is None:
        interval_sec = settings.FRAME_INTERVAL_SEC
    if max_frames is None:
        max_frames = settings.MAX_FRAMES
    if resize_dims is None:
        resize_dims = settings.FRAME_RESIZE

    str_path = str(video_path.resolve())
    cap = cv2.VideoCapture(str_path)

    if not cap.isOpened():
        raise ValueError(f"Corrupted or unsupported video stream: unable to open '{video_path.name}'")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Defense against broken or variable frame-rate headers
        if fps <= 0 or total_frame_count <= 0:
            raise ValueError(f"Invalid video metadata: fps={fps}, total_frames={total_frame_count}")

        duration_sec = total_frame_count / fps
        frame_step = max(1, int(fps * interval_sec))

        logger.info(
            "Stage 3 Frame Extraction: %s (fps=%.2f, total_frames=%d, duration=%.2fs, step=%d)",
            video_path.name, fps, total_frame_count, duration_sec, frame_step
        )

        target_frame_indices = set()
        # 1. First frame (index 0)
        target_frame_indices.add(0)

        # 2. Every interval_sec
        curr = 0
        while curr < total_frame_count:
            target_frame_indices.add(curr)
            curr += frame_step

        # 3. Last frame
        if total_frame_count > 1:
            target_frame_indices.add(total_frame_count - 1)

        # Sort indices chronologically
        sorted_indices = sorted(target_frame_indices)

        # Cap at max_frames if video is very long
        if len(sorted_indices) > max_frames:
            # Subsample evenly across the list
            step = len(sorted_indices) / max_frames
            sorted_indices = [sorted_indices[int(i * step)] for i in range(max_frames)]

        extracted_frames: List[Tuple[float, Image.Image]] = []

        for frame_idx in sorted_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            success, bgr_frame = cap.read()

            if not success or bgr_frame is None:
                logger.warning("Failed to decode frame at index %d in %s", frame_idx, video_path.name)
                continue

            # Calculate actual timestamp
            timestamp = round(frame_idx / fps, 3)

            # Resize to safe resolution (width, height)
            resized = cv2.resize(bgr_frame, resize_dims, interpolation=cv2.INTER_AREA)

            # Convert BGR (OpenCV) -> RGB (PIL/PyTorch)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_frame)

            extracted_frames.append((timestamp, pil_img))

        if not extracted_frames:
            raise ValueError(f"Fail-closed: No readable visual frames could be decoded from '{video_path.name}'")

        logger.info("Stage 3 SUCCESS: Extracted %d frames from %s", len(extracted_frames), video_path.name)
        return extracted_frames

    finally:
        cap.release()


def extract_24fps_frames_with_meta(
    video_path: Path,
    max_seconds: int = 4,
    max_frames: int = 96,
    thumbnail_dims: Tuple[int, int] = (240, 180),
) -> List[Dict[str, Any]]:
    """
    Extracts high-resolution 24 FPS temporal frames with rich metadata and base64 thumbnails.
    Extracts exactly 24 frames per second across video duration (bounded to max_seconds).
    
    Args:
        video_path: Path to target video file.
        max_seconds: Maximum seconds of video to process at 24fps (default: 4 seconds = 96 frames max).
        max_frames: Upper bound cap on extracted frames.
        thumbnail_dims: (width, height) for frontend thumbnail rendering.
        
    Returns:
        List of dicts containing frame indices, timestamps, numpy BGR frames, PIL Images, and base64 thumbnails.
    """
    import base64

    str_path = str(video_path.resolve())
    cap = cv2.VideoCapture(str_path)
    if not cap.isOpened():
        raise ValueError(f"Unable to open video stream: '{video_path.name}'")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0 or total_frames <= 0:
            raise ValueError(f"Invalid video container metadata: fps={fps}, total_frames={total_frames}")

        duration_sec = total_frames / fps
        process_seconds = max(1, min(int(np.ceil(duration_sec)), max_seconds))

        results = []
        global_idx = 1

        for sec in range(process_seconds):
            for sub_idx in range(24):
                if len(results) >= max_frames:
                    break

                target_time = sec + (sub_idx / 24.0)
                if target_time > duration_sec and results:
                    break

                target_frame_num = int(round(target_time * fps))
                if target_frame_num >= total_frames:
                    target_frame_num = max(0, total_frames - 1)

                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame_num)
                ret, bgr_frame = cap.read()
                if not ret or bgr_frame is None:
                    continue

                # Generate lightweight thumbnail
                thumb = cv2.resize(bgr_frame, thumbnail_dims, interpolation=cv2.INTER_AREA)
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 75]
                _, enc_bytes = cv2.imencode(".jpg", thumb, encode_param)
                b64_str = "data:image/jpeg;base64," + base64.b64encode(enc_bytes).decode("ascii")

                # Edge gradient visualization preview
                gray_thumb = cv2.cvtColor(thumb, cv2.COLOR_BGR2GRAY)
                lap_edge = cv2.Laplacian(gray_thumb, cv2.CV_8U)
                lap_color = cv2.applyColorMap(lap_edge, cv2.COLORMAP_JET)
                _, edge_bytes = cv2.imencode(".jpg", lap_color, encode_param)
                edge_b64_str = "data:image/jpeg;base64," + base64.b64encode(edge_bytes).decode("ascii")

                rgb_frame = cv2.cvtColor(thumb, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_frame)

                m, s_frac = divmod(target_time, 60)
                ts_str = f"{int(m):02d}:{s_frac:05.2f}"

                results.append({
                    "frame_index": global_idx,
                    "second_idx": sec,
                    "sub_second_frame": sub_idx + 1,
                    "timestamp_sec": round(target_time, 3),
                    "timestamp_str": ts_str,
                    "bgr_frame": thumb,
                    "pil_image": pil_img,
                    "thumbnail_data": b64_str,
                    "edge_data": edge_b64_str,
                })
                global_idx += 1

        logger.info("24 FPS Extraction SUCCESS: Generated %d frames for %s", len(results), video_path.name)
        return results

    finally:
        cap.release()
