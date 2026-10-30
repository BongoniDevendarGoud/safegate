"""
SafeGate — Deepfake & Synthetic Media Risk Scorer (Pipeline Stage 7)
====================================================================
Computes an advisory manipulation risk score (0 to 100) combining
lightweight temporal, spatial, and container-level heuristics.

HEURISTIC SIGNALS:
1. Face Sharpness / Blur Inconsistency (Weight: 30%):
   Uses OpenCV Haar cascades to isolate face bounding boxes across frames.
   Computes the Laplacian variance (sharpness metric). Deepfakes and face-swap
   models often exhibit unnatural sharpness jumps or excessive boundary blurring
   relative to the background.
2. Temporal Flicker & Inconsistency (Weight: 25%):
   Measures frame-to-frame color histogram correlation. Synthetically generated
   videos often exhibit jitter, warping, or sudden luminance discontinuities.
3. Compression Artifact Discrepancies (Weight: 25%):
   Calculates error residuals between original frames and JPEG recompression.
   Generative AI content and spliced faces frequently have mismatched quantization
   noise tables compared to natural sensor captures.
4. Container & Metadata Anomalies (Weight: 20%):
   Inspects container signatures for signs of re-encoding or absent camera metadata
   (e.g., synthetic encoders like Lavf, missing device make/model).

ADVISORY-ONLY RULE:
Deepfake risk is strictly PROBABILISTIC. A score >= DEEPFAKE_REVIEW_THRESHOLD
NEVER auto-blocks; it marks the upload for REVIEW and displays the breakdown
of detected anomalies to the human moderator.
"""

import io
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any
import cv2
import numpy as np
from PIL import Image
from app.config import settings

logger = logging.getLogger(__name__)


def compute_laplacian_variance(gray_img: np.ndarray) -> float:
    """
    Computes the focus/sharpness metric using the variance of the Laplacian.
    Higher values indicate sharp edges; lower values indicate blur.
    """
    return float(cv2.Laplacian(gray_img, cv2.CV_64F).var())


def evaluate_face_sharpness_inconsistency(frames: List[Tuple[float, Image.Image]]) -> Tuple[int, List[str]]:
    """
    Signal 1: Evaluates facial / foreground subject sharpness variance across frames.
    Uses Haar cascade if supported by OpenCV runtime; falls back to center-weighted
    subject ROI analysis.
    """
    score = 0
    reasons = []

    face_variances = []
    has_cascade = hasattr(cv2, "CascadeClassifier") and hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades")

    face_cascade = None
    if has_cascade:
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            logger.debug("CascadeClassifier init skipped: %s", e)
            face_cascade = None

    for ts, img in frames:
        np_frame = np.array(img)
        gray = cv2.cvtColor(np_frame, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape

        if face_cascade is not None and not face_cascade.empty():
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=4, minSize=(30, 30))
            for (x, y, fw, fh) in faces:
                face_roi = gray[y : y + fh, x : x + fw]
                var = compute_laplacian_variance(face_roi)
                face_variances.append(var)
        else:
            # Center-crop subject ROI (central 50% where facial/human subjects are positioned)
            y1, y2 = int(h * 0.25), int(h * 0.75)
            x1, x2 = int(w * 0.25), int(w * 0.75)
            center_roi = gray[y1:y2, x1:x2]
            var = compute_laplacian_variance(center_roi)
            face_variances.append(var)

    if len(face_variances) >= 3:
        arr = np.array(face_variances)
        mean_var = np.mean(arr)
        std_var = np.std(arr)

        # Coefficient of variation (std / mean)
        cov = std_var / (mean_var + 1e-5)
        if cov > 0.85:
            score = 30
            reasons.append(f"High inter-frame face/subject sharpness instability (CoV: {cov:.2f})")
        elif cov > 0.60:
            score = 15
            reasons.append(f"Moderate subject boundary sharpness variance (CoV: {cov:.2f})")

    return (score, reasons)


def evaluate_temporal_flicker(frames: List[Tuple[float, Image.Image]]) -> Tuple[int, List[str]]:
    """
    Signal 2: Detects sudden inter-frame visual discontinuities (temporal flickering).
    """
    if len(frames) < 2:
        return (0, [])

    score = 0
    reasons = []
    correlations = []

    for i in range(len(frames) - 1):
        img1 = np.array(frames[i][1])
        img2 = np.array(frames[i + 1][1])

        # Compute normalized color histograms
        hist1 = cv2.calcHist([img1], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist2 = cv2.calcHist([img2], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])

        cv2.normalize(hist1, hist1)
        cv2.normalize(hist2, hist2)

        # Correlation between adjacent frames (1.0 = identical distribution)
        corr = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        correlations.append(corr)

    if correlations:
        min_corr = min(correlations)
        avg_corr = sum(correlations) / len(correlations)

        # Unusually low correlation between adjacent video frames indicates splicing or generative warping
        if min_corr < 0.35:
            score = 25
            reasons.append(f"Severe temporal color discontinuity between consecutive frames (min corr: {min_corr:.2f})")
        elif min_corr < 0.60 or avg_corr < 0.80:
            score = 15
            reasons.append(f"Noticeable inter-frame luminance/color flicker (avg corr: {avg_corr:.2f})")

    return (score, reasons)


def evaluate_compression_artifacts(frames: List[Tuple[float, Image.Image]]) -> Tuple[int, List[str]]:
    """
    Signal 3: Compression inconsistency via JPEG recompression error residual analysis.
    """
    if not frames:
        return (0, [])

    score = 0
    reasons = []
    error_residuals = []

    # Sample up to 5 frames
    sample_frames = frames[:: max(1, len(frames) // 5)]
    for ts, img in sample_frames:
        # Save to JPEG in-memory and re-read
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        buf.seek(0)
        recompressed = Image.open(buf)

        orig_np = np.array(img, dtype=np.float32)
        recomp_np = np.array(recompressed, dtype=np.float32)

        # Mean squared error residual
        mse = float(np.mean((orig_np - recomp_np) ** 2))
        error_residuals.append(mse)

    if error_residuals:
        max_err = max(error_residuals)
        avg_err = sum(error_residuals) / len(error_residuals)
        # Deepfakes often lack native camera sensor noise and have abnormal quantization error
        if avg_err > 45.0:
            score = 25
            reasons.append(f"Anomalous high-frequency compression residuals (avg MSE: {avg_err:.1f})")
        elif avg_err > 30.0:
            score = 12
            reasons.append(f"Moderate compression artifact irregularities (avg MSE: {avg_err:.1f})")

    return (score, reasons)


def evaluate_container_metadata(video_path: Path) -> Tuple[int, List[str]]:
    """
    Signal 4: Inspects container headers for re-encoding signatures or missing camera tags.
    """
    score = 0
    reasons = []

    try:
        # Read first 16KB of container header
        with open(video_path, "rb") as f:
            header_chunk = f.read(16384)

        # Check for typical synthetic / re-encoder markers (Lavf/FFmpeg) vs camera hardware
        header_str = header_chunk.decode("latin-1", errors="ignore")
        if "Lavf" in header_str or "HandBrake" in header_str:
            score += 10
            reasons.append("Container indicates third-party transcoding / synthetic pipeline (Lavf signature)")

        # Lack of standard camera metadata (Apple, Sony, Canon, Samsung, Android)
        known_camera_brands = ["Apple", "Sony", "Canon", "Nikon", "Samsung", "Google", "Panasonic"]
        has_camera_brand = any(brand in header_str for brand in known_camera_brands)
        if not has_camera_brand:
            score += 10
            reasons.append("Absence of authentic camera manufacturer metadata tags in media container")

    except Exception as e:
        logger.warning("Metadata inspection error on %s: %s", video_path.name, e)

    return (min(20, score), reasons)


def calculate_deepfake_risk(
    video_path: Path,
    frames: List[Tuple[float, Image.Image]],
) -> Tuple[int, List[str]]:
    """
    Aggregates all heuristic signals into a composite probabilistic score (0 - 100).

    Returns:
        Tuple of (risk_score: int [0-100], reasons: list of strings)
    """
    total_score = 0
    all_reasons = []

    # Signal 1: Face Sharpness
    s1, r1 = evaluate_face_sharpness_inconsistency(frames)
    total_score += s1
    all_reasons.extend(r1)

    # Signal 2: Temporal Flicker
    s2, r2 = evaluate_temporal_flicker(frames)
    total_score += s2
    all_reasons.extend(r2)

    # Signal 3: Compression Artifacts
    s3, r3 = evaluate_compression_artifacts(frames)
    total_score += s3
    all_reasons.extend(r3)

    # Signal 4: Metadata Anomalies
    s4, r4 = evaluate_container_metadata(video_path)
    total_score += s4
    all_reasons.extend(r4)

    # Normalize to 0-100 range
    final_score = max(0, min(100, total_score))

    logger.info(
        "Stage 7 Deepfake Heuristic Assessment: score=%d/100, signals_detected=%d",
        final_score, len(all_reasons)
    )

    return (final_score, all_reasons)
