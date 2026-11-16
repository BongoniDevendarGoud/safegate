"""
SafeGate Multi-Branch Pipeline Orchestrator.
Executes spatial, frequency, temporal, and sensitive branches on each frame.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch

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

    def __init__(
        self,
        detector_type: str = "heuristic",
        model_version: str = "0.1.0-heuristic",
        model_checksum: str | None = None,
        has_validated_model: bool = False,
        has_calibrated_thresholds: bool = False,
    ) -> None:
        self.detector_type = detector_type
        self.model_version = model_version
        self.model_checksum = model_checksum
        self.has_validated_model = has_validated_model
        self.has_calibrated_thresholds = has_calibrated_thresholds
        self.spatial_detector = SpatialDetector()
        self.frequency_detector = FrequencyDetector()
        self.temporal_detector = TemporalDetector()
        self.sensitive_classifier = SensitiveContentClassifier()
        self.neural_model: Any = None

        # Check for registered validated neural model checkpoint
        manifest_path = Path("models/model_manifest.json")
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
                if manifest.get("status") == "VALIDATED":
                    ckpt_file = Path("models/checkpoints") / manifest.get("checkpoint_file", "")
                    if ckpt_file.exists():
                        actual_sha = hashlib.sha256(ckpt_file.read_bytes()).hexdigest()
                        if actual_sha == manifest.get("sha256_checksum"):
                            from ml.models.dual_stream import SpatialFrequencyDualStreamDetector

                            net = SpatialFrequencyDualStreamDetector()
                            net.load_state_dict(torch.load(str(ckpt_file), map_location="cpu"))
                            net.eval()
                            self.neural_model = net
                            self.detector_type = "model"
                            self.has_validated_model = True
                            self.has_calibrated_thresholds = True
                            self.model_version = manifest.get("version", "1.0.0")
                            self.model_checksum = actual_sha
            except Exception:
                self.neural_model = None

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

        # If validated neural network model is loaded, execute dual-stream inference
        if self.neural_model is not None:
            try:
                resized = cv2.resize(rgb_frame, (128, 128))
                norm_img = np.transpose(resized.astype(np.float32) / 255.0, (2, 0, 1))
                t_img = torch.tensor(norm_img[np.newaxis, ...], dtype=torch.float32)

                gray = cv2.cvtColor(resized, cv2.COLOR_RGB2GRAY)
                f_transform = np.fft.fftshift(np.fft.fft2(gray.astype(np.float32)))
                magnitude_spectrum = np.log(np.abs(f_transform) + 1.0)
                h, w = magnitude_spectrum.shape
                cy, cx = h // 2, w // 2
                max_r = min(cy, cx)
                radial_bins = np.zeros(64, dtype=np.float32)
                for r_idx in range(64):
                    r_rad = int(r_idx * (max_r / 64))
                    radial_bins[r_idx] = float(
                        np.mean(magnitude_spectrum[cy - r_rad : cy + r_rad + 1, cx - r_rad : cx + r_rad + 1])
                    )
                t_freq = torch.tensor(radial_bins[np.newaxis, ...], dtype=torch.float32)

                neural_prob = self.neural_model.predict_probability(t_img, t_freq)
                spatial_res = SpatialResult(
                    manipulation_score=neural_prob,
                    confidence=0.95,
                    face_detected=spatial_res.face_detected,
                    face_count=spatial_res.face_count,
                    cues={**spatial_res.cues, "neural_prob": round(neural_prob, 4), "model_inference": True},
                )
                freq_res = FrequencyResult(
                    manipulation_score=neural_prob,
                    spectral_falloff_slope=freq_res.spectral_falloff_slope,
                    high_freq_ratio=freq_res.high_freq_ratio,
                    grid_artifact_detected=freq_res.grid_artifact_detected,
                    cues={**freq_res.cues, "neural_prob": round(neural_prob, 4)},
                )
            except Exception:
                pass

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
