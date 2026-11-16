"""
Branch 3: Temporal Consistency & Optical Flow Detector.
Measures inter-frame motion trajectories, optical flow velocity anomalies,
and frame-to-frame jitter characteristic of deepfake video reenactment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class TemporalResult:
    anomaly_score: float  # [0.0, 1.0]
    mean_flow_magnitude: float
    flow_variance: float
    is_first_frame: bool
    cues: dict[str, Any]


class TemporalDetector:
    """
    Maintains state across consecutive video frames to calculate dense optical flow
    and temporal continuity scores.
    """

    def __init__(self) -> None:
        self.prev_gray: np.ndarray | None = None
        self.prev_flow_mag: float | None = None

    def reset(self) -> None:
        """Resets temporal tracking state for a new video sequence."""
        self.prev_gray = None
        self.prev_flow_mag = None

    def analyze_frame(self, rgb_frame: np.ndarray) -> TemporalResult:
        """
        Analyzes current frame relative to previous frame.
        """
        gray = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2GRAY)
        # Downscale for real-time dense optical flow calculation
        h, w = gray.shape
        scale = 320.0 / max(h, w)
        if scale < 1.0:
            small_gray = cv2.resize(
                gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
            )
        else:
            small_gray = gray

        if self.prev_gray is None:
            self.prev_gray = small_gray
            return TemporalResult(
                anomaly_score=0.0,
                mean_flow_magnitude=0.0,
                flow_variance=0.0,
                is_first_frame=True,
                cues={"first_frame": True},
            )

        # Compute Gunnar Farnebäck dense optical flow
        flow = cv2.calcOpticalFlowFarneback(  # type: ignore[call-overload]
            prev=self.prev_gray,
            next=small_gray,
            flow=None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0,
        )

        flow_x, flow_y = flow[..., 0], flow[..., 1]
        magnitude, angle = cv2.cartToPolar(flow_x, flow_y)

        mean_mag = float(np.mean(magnitude))
        var_mag = float(np.var(magnitude))

        # Check for unnatural velocity acceleration between frames (jitter)
        anomaly_score = 0.0
        accel = 0.0
        if self.prev_flow_mag is not None:
            accel = abs(mean_mag - self.prev_flow_mag)
            # Sudden velocity spikes without scene cut indicate warping flickers
            if accel > 8.0:
                anomaly_score = min(1.0, 0.4 + (accel - 8.0) * 0.05)
            elif accel > 4.5:
                anomaly_score = 0.35

        # Check high flow variance combined with moderate mean flow (localized warping)
        if var_mag > 15.0 and mean_mag < 3.0:
            anomaly_score = max(anomaly_score, 0.45)

        self.prev_gray = small_gray
        self.prev_flow_mag = mean_mag

        return TemporalResult(
            anomaly_score=round(anomaly_score, 4),
            mean_flow_magnitude=round(mean_mag, 4),
            flow_variance=round(var_mag, 4),
            is_first_frame=False,
            cues={
                "mean_flow": round(mean_mag, 4),
                "var_flow": round(var_mag, 4),
                "acceleration": round(accel, 4),
            },
        )
