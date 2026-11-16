"""
SafeGate Multi-Branch Pipeline Orchestrator.
Executes spatial, frequency, temporal, and sensitive branches on each frame.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ml.detectors.frequency import FrequencyDetector, FrequencyResult
from ml.detectors.sensitive import SensitiveContentClassifier, SensitiveResult
from ml.detectors.spatial import SpatialDetector, SpatialResult
from ml.detectors.temporal import TemporalDetector, TemporalResult


@dataclass(frozen=True)
class MultiBranchFrameResult:
    frame_index: int
    timestamp_ms: int
    spatial: SpatialResult
    frequency: FrequencyResult
    temporal: TemporalResult
    sensitive: SensitiveResult
    cues: dict[str, Any]


class MultiBranchPipeline:
    """
    Coordinates extraction of spatial, spectral, temporal, and sensitive cues for each frame.
    """

    def __init__(self) -> None:
        self.spatial_detector = SpatialDetector()
        self.frequency_detector = FrequencyDetector()
        self.temporal_detector = TemporalDetector()
        self.sensitive_classifier = SensitiveContentClassifier()

    def reset(self) -> None:
        """Resets state for a new video sequence."""
        self.temporal_detector.reset()

    def process_frame(
        self,
        rgb_frame: np.ndarray,
        frame_index: int = 0,
        timestamp_ms: int = 0,
    ) -> MultiBranchFrameResult:
        """
        Runs all detector branches concurrently or sequentially on a single RGB frame.
        """
        spatial_res = self.spatial_detector.analyze_frame(rgb_frame)
        freq_res = self.frequency_detector.analyze_frame(rgb_frame)
        temporal_res = self.temporal_detector.analyze_frame(rgb_frame)
        sensitive_res = self.sensitive_classifier.analyze_frame(rgb_frame)

        aggregated_cues: dict[str, Any] = {
            "spatial": spatial_res.cues,
            "frequency": freq_res.cues,
            "temporal": temporal_res.cues,
            "sensitive": sensitive_res.cues,
        }

        return MultiBranchFrameResult(
            frame_index=frame_index,
            timestamp_ms=timestamp_ms,
            spatial=spatial_res,
            frequency=freq_res,
            temporal=temporal_res,
            sensitive=sensitive_res,
            cues=aggregated_cues,
        )
