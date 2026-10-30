"""
SafeGate OSI Model — Layer 2: Data Link / Framing Layer
========================================================
OSI MAPPING:
In traditional networking, Layer 2 (Data Link) groups raw bits into structured
"Frames" and manages flow synchronization.
In SafeGate, Layer 2 transforms the continuous temporal video stream into discrete
image frames:
- Frame extraction using temporal sampling (first frame, interval frames, last frame).
- Frame rate & timestamp synchronization.
- Bounded frame capping (MAX_FRAMES) to prevent framing-based resource exhaustion.

VIVA EXPLANATION:
Why is frame extraction mapped to Layer 2?
Because the Data Link layer is responsible for "framing"—taking an unstructured bitstream
and delineating discrete message units (frames). Without Layer 2 framing, higher-layer
vision classifiers cannot operate on temporal video data.
"""

from pathlib import Path
from typing import List, Tuple
from PIL import Image
from app.config import settings
from app.pipeline.frame_extraction import extract_video_frames


class Layer2DataLinkFraming:
    """
    Layer 2: Frame Delineation & Temporal Synchronization.
    """

    def __init__(self, interval_sec: int = None, max_frames: int = None):
        self.interval_sec = interval_sec or settings.FRAME_INTERVAL_SEC
        self.max_frames = max_frames or settings.MAX_FRAMES

    def extract_frames(self, video_path: Path) -> List[Tuple[float, Image.Image]]:
        """
        Samples discrete frames from the video container file.

        Returns:
            List of (timestamp_in_seconds, PIL.Image) tuples.

        Raises:
            ValueError: If container has 0 frames or cannot be decoded.
        """
        frames = extract_video_frames(
            video_path=video_path,
            interval_sec=self.interval_sec,
            max_frames=self.max_frames,
        )
        if not frames:
            raise ValueError("[Layer 2 Framing Violation] No decodable frames identified in bitstream.")
        return frames
