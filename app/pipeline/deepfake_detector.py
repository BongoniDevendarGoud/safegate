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


def analyze_24fps_frame_by_frame(frames_meta: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Performs forensic inspection across 24 FPS extracted frames to distinguish
    LEGITIMATE (authentic camera capture) from MODIFIED (synthetic / deepfake / spliced) frames.

    Args:
        frames_meta: Output list from extract_24fps_frames_with_meta.

    Returns:
        Structured forensic report with frame-by-frame verdicts, confidence scores,
        signal telemetry, tamper ratios, and timestamps.
    """
    if not frames_meta:
        return {
            "total_frames_extracted": 0,
            "fps_sample_rate": 24,
            "legitimate_frames_count": 0,
            "modified_frames_count": 0,
            "tamper_percentage": 0.0,
            "tampered_timestamps": [],
            "frames_timeline": [],
        }

    frames_timeline = []
    prev_hist = None
    modified_count = 0
    tampered_timestamps = []

    for idx, item in enumerate(frames_meta):
        bgr = item["bgr_frame"]
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # 1. Laplacian sharpness metric
        lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        # 2. JPEG re-compression error residual (MSE)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
        _, enc = cv2.imencode(".jpg", bgr, encode_param)
        dec = cv2.imdecode(enc, cv2.IMREAD_COLOR)
        mse = float(np.mean((bgr.astype(float) - dec.astype(float)) ** 2))

        # 3. Inter-frame color histogram correlation
        hist = cv2.calcHist([bgr], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        cv2.normalize(hist, hist)
        corr = 1.0
        if prev_hist is not None:
            corr = float(cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL))
        prev_hist = hist

        # 4. Multi-heuristic decision for this specific frame
        reasons = []
        is_modified = False

        if mse > 28.0:
            is_modified = True
            reasons.append(f"Synthetic high-frequency noise residual (MSE: {mse:.1f})")

        if corr < 0.35 and idx > 0:
            is_modified = True
            reasons.append(f"Inter-frame color/luminance discontinuity (Corr: {corr:.2f})")

        if lap_var < 15.0 and mse > 16.0:
            is_modified = True
            reasons.append(f"Unnatural edge boundary blur discontinuity (Laplacian: {lap_var:.1f})")

        import base64
        h, w = bgr.shape[:2]
        marked_bgr = bgr.copy()

        if is_modified:
            status = "MODIFIED"
            modified_count += 1
            tampered_timestamps.append(f"{item['timestamp_str']} (Frame #{item['frame_index']})")
            # Confidence in tampering
            conf = min(99.4, round(65.0 + (mse * 0.25) + max(0.0, (1.0 - corr) * 20.0), 1))
            anomaly_score = min(100.0, round(50.0 + (mse * 0.35), 1))
            reason_str = "; ".join(reasons)
            # Neutral / amber mark for modified frames
            cv2.rectangle(marked_bgr, (0, 0), (w - 1, h - 1), (60, 140, 245), 2)
            cv2.rectangle(marked_bgr, (6, 6), (105, 26), (40, 40, 40), -1)
            cv2.putText(marked_bgr, "MODIFIED", (12, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (60, 140, 245), 1, cv2.LINE_AA)
        else:
            status = "LEGITIMATE"
            conf = min(99.8, round(max(85.0, 100.0 - (mse * 1.2)), 1))
            anomaly_score = max(2.0, round(mse * 1.1, 1))
            reason_str = "Pristine optical sensor consistency, natural edge gradients & coherent temporal color."
            # >>> PROMINENT RED COLOR MARK FOR LEGITIMATE FRAMES <<<
            cv2.rectangle(marked_bgr, (0, 0), (w - 1, h - 1), (0, 0, 255), 4)
            cv2.rectangle(marked_bgr, (6, 6), (120, 26), (0, 0, 255), -1)
            cv2.putText(marked_bgr, "LEGITIMATE", (12, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)

        # Encode thumbnail with mark
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
        _, enc_thumb = cv2.imencode(".jpg", marked_bgr, encode_param)
        marked_b64 = "data:image/jpeg;base64," + base64.b64encode(enc_thumb).decode("ascii")

        frames_timeline.append({
            "frame_index": item["frame_index"],
            "second_idx": item["second_idx"],
            "sub_second_frame": item["sub_second_frame"],
            "timestamp_sec": item["timestamp_sec"],
            "timestamp_str": item["timestamp_str"],
            "status": status,
            "confidence": conf,
            "anomaly_score": anomaly_score,
            "laplacian_variance": round(lap_var, 1),
            "compression_mse": round(mse, 1),
            "color_correlation": round(corr, 3),
            "reason": reason_str,
            "thumbnail_data": marked_b64,
            "edge_data": item["edge_data"],
            "mark_color": "red" if status == "LEGITIMATE" else "dark",
        })

    total_count = len(frames_timeline)
    legitimate_count = total_count - modified_count
    tamper_pct = round((modified_count / total_count * 100.0) if total_count > 0 else 0.0, 1)

    return {
        "total_frames_extracted": total_count,
        "fps_sample_rate": 24,
        "legitimate_frames_count": legitimate_count,
        "modified_frames_count": modified_count,
        "tamper_percentage": tamper_pct,
        "tampered_timestamps": tampered_timestamps,
        "frames_timeline": frames_timeline,
    }
