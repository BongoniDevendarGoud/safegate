"""
Branch 2: Frequency & Diffusion Fingerprint Detector.
Performs 2D FFT and DCT power spectrum analysis to uncover GAN upsampling grids,
diffusion noise irregularities, and high-frequency spectral anomalies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class FrequencyResult:
    manipulation_score: float  # [0.0, 1.0]
    spectral_falloff_slope: float
    high_freq_ratio: float
    grid_artifact_detected: bool
    cues: dict[str, Any]


class FrequencyDetector:
    """
    Analyzes frequency domain characteristics via 2D FFT power spectrum and radial profile.
    """

    def analyze_frame(self, rgb_frame: np.ndarray) -> FrequencyResult:
        """
        Computes 2D FFT power spectrum and checks deviation from 1/f^alpha natural image statistics.
        """
        gray = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape

        # Downsample or crop to central 256x256 patch for uniform spectral comparison
        target_size = 256
        if h > target_size and w > target_size:
            cy, cx = h // 2, w // 2
            half = target_size // 2
            patch = gray[cy - half : cy + half, cx - half : cx + half]
        else:
            patch = cv2.resize(gray, (target_size, target_size), interpolation=cv2.INTER_AREA)

        # 2D Fast Fourier Transform with zero-frequency centered
        f_transform = np.fft.fft2(patch.astype(np.float32))
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = np.abs(f_shift)
        power_spectrum = magnitude_spectrum**2

        # Radial profile calculation from center DC component
        cy, cx = target_size // 2, target_size // 2
        y, x = np.ogrid[:target_size, :target_size]
        r = np.hypot(x - cx, y - cy).astype(int)

        # Calculate mean power at each radial frequency bin
        max_r = target_size // 2
        radial_prof = np.zeros(max_r, dtype=np.float32)
        for radius in range(1, max_r):
            mask = r == radius
            if np.any(mask):
                radial_prof[radius] = float(np.mean(power_spectrum[mask]))

        # Normalize profile
        prof_valid = radial_prof[1:]
        prof_valid = prof_valid / (np.max(prof_valid) + 1e-10)

        # Fit log-log slope for natural 1/f decay
        freq_indices = np.arange(1, len(prof_valid) + 1)
        log_freq = np.log(freq_indices)
        log_power = np.log(prof_valid + 1e-10)

        # Linear regression slope (natural images typically exhibit slope between -1.8 and -2.4)
        if len(log_freq) > 5:
            poly = np.polyfit(log_freq, log_power, deg=1)
            slope = float(poly[0])
        else:
            slope = -2.0

        # High-frequency power ratio (outer 30% of radial spectrum)
        high_freq_start = int(max_r * 0.7)
        total_energy = float(np.sum(radial_prof[1:])) + 1e-10
        high_freq_energy = float(np.sum(radial_prof[high_freq_start:]))
        high_freq_ratio = float(high_freq_energy / total_energy)

        # Checkerboard / periodic grid peak detection in high-frequency quadrants
        # GAN and transposed convolution models produce prominent 4-fold symmetrical peaks
        quadrant_std = float(np.std(magnitude_spectrum[max_r - 20 : max_r + 20, :20]))
        center_std = float(
            np.std(magnitude_spectrum[max_r - 20 : max_r + 20, max_r - 20 : max_r + 20])
        )
        grid_ratio = quadrant_std / (center_std + 1e-5)
        grid_artifact_detected = grid_ratio > 0.45

        # Score computation based on deviation from natural image statistics
        # Natural images typically exhibit radial slope between -1.5 and -3.2
        slope_deviation = abs(slope - (-2.2))
        manipulation_score = 0.0

        if slope_deviation > 1.3:
            manipulation_score += 0.40
        elif slope_deviation > 0.9:
            manipulation_score += 0.25

        if grid_artifact_detected:
            manipulation_score += 0.45

        if high_freq_ratio > 0.18:
            manipulation_score += 0.30

        manipulation_score = float(np.clip(manipulation_score, 0.0, 1.0))

        return FrequencyResult(
            manipulation_score=manipulation_score,
            spectral_falloff_slope=round(slope, 4),
            high_freq_ratio=round(high_freq_ratio, 6),
            grid_artifact_detected=grid_artifact_detected,
            cues={
                "slope": round(slope, 4),
                "high_freq_ratio": round(high_freq_ratio, 6),
                "grid_ratio": round(grid_ratio, 4),
                "grid_artifact_detected": grid_artifact_detected,
            },
        )
