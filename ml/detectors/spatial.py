"""
Branch 1: Spatial Face & Image Manipulation Detector.
Detects facial boundary blending, splicing anomalies, warping artifacts, and synthetic face swaps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class SpatialResult:
    manipulation_score: float  # [0.0, 1.0]
    confidence: float  # [0.0, 1.0]
    face_detected: bool
    face_count: int
    cues: dict[str, Any]


class SpatialDetector:
    """
    Spatial feature extractor examining facial crop boundaries, gradient discontinuities,
    and digital manipulation residuals.
    """

    def __init__(self) -> None:
        self.face_cascade: Any = None
        if hasattr(cv2, "CascadeClassifier") and hasattr(cv2, "data"):
            try:
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"  # type: ignore[attr-defined]
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
            except Exception:
                self.face_cascade = None

    def _locate_faces(self, rgb_frame: np.ndarray) -> list[tuple[int, int, int, int]]:
        """
        Locates face bounding boxes using Haar Cascade if available,
        falling back to chromatic skin-locus contour localization.
        """
        h, w = rgb_frame.shape[:2]
        faces: list[tuple[int, int, int, int]] = []

        # 1. Try Haar Cascade if available
        if self.face_cascade is not None:
            gray = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2GRAY)
            detected = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=4, minSize=(32, 32)
            )
            if len(detected) > 0:
                return [(int(x), int(y), int(bw), int(bh)) for (x, y, bw, bh) in detected]

        # 2. Chromatic skin-locus and head contour localization
        bgr = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
        ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
        skin_mask = cv2.inRange(
            ycrcb,
            np.array([0, 133, 77], dtype=np.uint8),
            np.array([255, 173, 127], dtype=np.uint8),
        )
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        clean_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        min_area = (h * w) * 0.02
        for c in contours:
            area = float(cv2.contourArea(c))
            if area > min_area:
                x, y, bw, bh = cv2.boundingRect(c)
                aspect = float(bh) / float(bw)
                if 0.75 <= aspect <= 2.5:  # Standard human head/face aspect ratio
                    faces.append((x, y, bw, bh))

        return faces

    def analyze_frame(self, rgb_frame: np.ndarray) -> SpatialResult:
        """
        Analyzes a single RGB frame for spatial synthesis artifacts.
        """
        gray = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape

        faces = self._locate_faces(rgb_frame)
        face_count = len(faces)
        face_detected = face_count > 0

        if face_detected:
            # Focus on largest candidate face
            largest_face = max(faces, key=lambda r: r[2] * r[3])
            fx, fy, fw, fh = largest_face

            # Extract face crop and surrounding margin for boundary analysis
            pad_w = int(fw * 0.15)
            pad_h = int(fh * 0.15)

            y1 = max(0, fy - pad_h)
            y2 = min(h, fy + fh + pad_h)
            x1 = max(0, fx - pad_w)
            x2 = min(w, fx + fw + pad_w)

            face_roi = gray[y1:y2, x1:x2]
            inner_face = gray[fy : fy + fh, fx : fx + fw]

            # 1. Boundary gradient analysis (face swap seam detection)
            laplacian_var_inner = float(cv2.Laplacian(inner_face, cv2.CV_64F).var())
            laplacian_var_boundary = float(cv2.Laplacian(face_roi, cv2.CV_64F).var())

            # Edge smoothness / blurring ratio at boundary
            ratio = (
                laplacian_var_inner / (laplacian_var_boundary + 1e-5)
                if laplacian_var_boundary > 0
                else 1.0
            )
            boundary_anomaly = float(np.clip(abs(1.0 - ratio) * 0.4, 0.0, 1.0))

            # 2. Color gradient mismatch (check across RGB channels)
            rgb_face = rgb_frame[fy : fy + fh, fx : fx + fw]
            mean_r = float(np.mean(rgb_face[:, :, 0]))
            mean_g = float(np.mean(rgb_face[:, :, 1]))
            mean_b = float(np.mean(rgb_face[:, :, 2]))

            # Check for unnatural color balance divergence
            color_divergence = float(
                np.clip(abs(mean_r - mean_b) / (mean_g + 1e-5) * 0.25, 0.0, 1.0)
            )

            # Combined spatial score
            raw_score = 0.6 * boundary_anomaly + 0.4 * color_divergence
            manipulation_score = float(np.clip(raw_score, 0.0, 1.0))
            confidence = 0.85

            cues = {
                "face_count": face_count,
                "largest_face_box": [int(fx), int(fy), int(fw), int(fh)],
                "boundary_anomaly": round(boundary_anomaly, 4),
                "color_divergence": round(color_divergence, 4),
                "inner_sharpness": round(laplacian_var_inner, 2),
            }

        else:
            # Fallback: Whole-image splice / noise consistency analysis
            laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            noise_residual = float(
                np.std(gray.astype(np.float32) - cv2.GaussianBlur(gray, (5, 5), 0))
            )

            # Natural camera sensor noise usually falls in [1.5, 8.0]
            if noise_residual < 0.8:
                # Artificial smoothness (common in synthetic diffusion outputs)
                manipulation_score = 0.55
            elif noise_residual > 18.0:
                manipulation_score = 0.60
            else:
                manipulation_score = 0.15

            confidence = 0.60
            cues = {
                "face_count": 0,
                "overall_sharpness": round(laplacian_var, 2),
                "noise_residual_std": round(noise_residual, 4),
                "fallback_mode": "full_image",
            }

        return SpatialResult(
            manipulation_score=manipulation_score,
            confidence=confidence,
            face_detected=face_detected,
            face_count=face_count,
            cues=cues,
        )
