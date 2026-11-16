"""
Branch 4: Dedicated Sensitive Content Classifier.
Specifically detects graphic violence, blood, gore, and adult nudity.
Kept strictly separate from deepfake detection models (routes to YELLOW for human review).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class SensitiveResult:
    sensitive_score: float  # [0.0, 1.0]
    is_blood_detected: bool
    is_nudity_detected: bool
    categories: dict[str, float]
    cues: dict[str, Any]


class SensitiveContentClassifier:
    """
    Dedicated analyzer evaluating graphic violence, blood pools, and nudity.
    """

    def analyze_frame(self, rgb_frame: np.ndarray) -> SensitiveResult:
        """
        Evaluates chromatic and textural distributions indicative of blood, gore, or nudity.
        """
        h, w = rgb_frame.shape[:2]
        total_pixels = float(h * w)

        # Convert to HSV and YCrCb
        bgr = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)

        # ---------------------------------------------------------
        # 1. Blood & Violence Detection (Deep crimson / hemoglobin spectrum)
        # ---------------------------------------------------------
        # Red hue wraps in HSV: [0, 10] and [170, 180]
        # Real blood typically has high saturation (S >= 100) and medium/dark value (V between 40 and 220)
        lower_red1 = np.array([0, 100, 40], dtype=np.uint8)
        upper_red1 = np.array([10, 255, 220], dtype=np.uint8)

        lower_red2 = np.array([170, 100, 40], dtype=np.uint8)
        upper_red2 = np.array([180, 255, 220], dtype=np.uint8)

        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        blood_mask = cv2.bitwise_or(mask1, mask2)

        # Filter small noise grains via morphological opening
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        clean_blood_mask = cv2.morphologyEx(blood_mask, cv2.MORPH_OPEN, kernel)

        blood_pixel_count = float(cv2.countNonZero(clean_blood_mask))
        blood_ratio = blood_pixel_count / total_pixels

        # Blood score calibration:
        # > 1.5% concentrated crimson is notable, > 5% is substantial
        blood_score = 0.0
        if blood_ratio > 0.06:
            blood_score = min(1.0, 0.70 + (blood_ratio - 0.06) * 5.0)
        elif blood_ratio > 0.015:
            blood_score = 0.40 + (blood_ratio - 0.015) * 6.5
        elif blood_ratio > 0.005:
            blood_score = 0.20

        is_blood_detected = blood_score >= 0.45

        # ---------------------------------------------------------
        # 2. Skin / Nudity Area Detection (YCrCb color space)
        # ---------------------------------------------------------
        # Standard human skin locus: Cr in [133, 173], Cb in [77, 127]
        lower_skin = np.array([0, 133, 77], dtype=np.uint8)
        upper_skin = np.array([255, 173, 127], dtype=np.uint8)

        skin_mask = cv2.inRange(ycrcb, lower_skin, upper_skin)
        clean_skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)

        skin_pixel_count = float(cv2.countNonZero(clean_skin_mask))
        skin_ratio = skin_pixel_count / total_pixels

        # High contiguous skin ratio (>35%) indicates potential nudity
        nudity_score = 0.0
        if skin_ratio > 0.50:
            nudity_score = min(1.0, 0.65 + (skin_ratio - 0.50) * 1.5)
        elif skin_ratio > 0.35:
            nudity_score = 0.45
        elif skin_ratio > 0.20:
            nudity_score = 0.20

        is_nudity_detected = nudity_score >= 0.50

        # Maximum sensitive score across categories
        sensitive_score = float(max(blood_score, nudity_score))

        categories = {
            "blood_violence": round(blood_score, 4),
            "nudity": round(nudity_score, 4),
        }

        cues = {
            "blood_ratio": round(blood_ratio, 5),
            "skin_ratio": round(skin_ratio, 4),
            "is_blood_detected": is_blood_detected,
            "is_nudity_detected": is_nudity_detected,
        }

        return SensitiveResult(
            sensitive_score=round(sensitive_score, 4),
            is_blood_detected=is_blood_detected,
            is_nudity_detected=is_nudity_detected,
            categories=categories,
            cues=cues,
        )
