"""
SafeGate — Frame Extraction Module (Pipeline Stage 3)
======================================================
Extracts representative visual frames from quarantined videos using OpenCV.

FAIL-CLOSED BEHAVIOR:
If OpenCV fails to open the video file or cannot decode valid frames,
a ValueError is raised so the orchestrator routes the file to REVIEW.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    """Extract temporally distributed frames from a video file on disk."""
    if interval_sec is None:
        interval_sec = settings.FRAME_INTERVAL_SEC
    if max_frames is None:
        max_frames = settings.MAX_FRAMES
    if resize_dims is None:
        resize_dims = settings.FRAME_RESIZE

    cap = cv2.VideoCapture(str(video_path.resolve()))
    if not cap.isOpened():
        raise ValueError(f"Corrupted or unsupported video stream: unable to open '{video_path.name}'")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if fps <= 0 or total_frame_count <= 0:
            raise ValueError(f"Invalid video metadata: fps={fps}, total_frames={total_frame_count}")

        duration_sec = total_frame_count / fps
        frame_step = max(1, int(fps * interval_sec))
        logger.info(
            "Stage 3 Frame Extraction: %s (fps=%.2f, total_frames=%d, duration=%.2fs, step=%d)",
            video_path.name, fps, total_frame_count, duration_sec, frame_step,
        )

        target_frame_indices = {0}
        curr = 0
        while curr < total_frame_count:
            target_frame_indices.add(curr)
            curr += frame_step
        if total_frame_count > 1:
            target_frame_indices.add(total_frame_count - 1)

        sorted_indices = sorted(target_frame_indices)
        if len(sorted_indices) > max_frames:
            step = len(sorted_indices) / max_frames
            sorted_indices = [sorted_indices[int(i * step)] for i in range(max_frames)]

        extracted_frames: List[Tuple[float, Image.Image]] = []
        for frame_idx in sorted_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            success, bgr_frame = cap.read()
            if not success or bgr_frame is None:
                logger.warning("Failed to decode frame at index %d in %s", frame_idx, video_path.name)
                continue

            timestamp = round(frame_idx / fps, 3)
            resized = cv2.resize(bgr_frame, resize_dims, interpolation=cv2.INTER_AREA)
            rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            extracted_frames.append((timestamp, Image.fromarray(rgb_frame)))

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
    """Extract high-resolution 24 FPS temporal frames with metadata and thumbnails."""
    import base64

    cap = cv2.VideoCapture(str(video_path.resolve()))
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

                thumb = cv2.resize(bgr_frame, thumbnail_dims, interpolation=cv2.INTER_AREA)
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 75]
                _, enc_bytes = cv2.imencode(".jpg", thumb, encode_param)
                b64_str = "data:image/jpeg;base64," + base64.b64encode(enc_bytes).decode("ascii")
                gray_thumb = cv2.cvtColor(thumb, cv2.COLOR_BGR2GRAY)
                lap_edge = cv2.Laplacian(gray_thumb, cv2.CV_8U)
                lap_color = cv2.applyColorMap(lap_edge, cv2.COLORMAP_JET)
                _, edge_bytes = cv2.imencode(".jpg", lap_color, encode_param)
                edge_b64_str = "data:image/jpeg;base64," + base64.b64encode(edge_bytes).decode("ascii")
                pil_img = Image.fromarray(cv2.cvtColor(thumb, cv2.COLOR_BGR2RGB))
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


def extract_all_video_frames(
    video_path: Path,
    upload_id: str,
    ai_engine: Any = None,
    max_frames: Optional[int] = None,
    save_frames_to_disk: bool = True,
    progress_callback: Optional[Any] = None,
) -> Dict[str, Any]:
    """Extract and classify every decoded video frame, storing forensic results."""
    import base64
    import hashlib

    from app.pipeline.ai_engine import (
        default_ai_engine,
        CLASS_LEGITIMATE,
        CLASS_SUSPICIOUS,
        CLASS_UNCERTAIN,
    )

    if ai_engine is None:
        ai_engine = default_ai_engine

    cap = cv2.VideoCapture(str(video_path.resolve()))
    if not cap.isOpened():
        raise ValueError(f"Corrupted or unsupported media stream: unable to decode '{video_path.name}'")

    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
        total_expected_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if fps <= 0 or (total_expected_frames <= 0 and max_frames is None):
            raise ValueError(f"Invalid video stream headers: fps={fps}, total_frames={total_expected_frames}")

        duration_sec = (total_expected_frames / fps) if total_expected_frames > 0 else 0.0
        frames_dir = settings.frames_path / upload_id
        if save_frames_to_disk:
            frames_dir.mkdir(parents=True, exist_ok=True)

        frames_results = []
        timeline_markers = []
        suspicious_timestamps = []
        suspicious_frame_refs = []
        decoded_count = legitimate_count = suspicious_count = uncertain_count = failed_count = 0
        prev_hist = None
        current_suspicious_run = []
        suspicious_segments = []

        while True:
            ret, bgr_frame = cap.read()
            if not ret or bgr_frame is None:
                break
            decoded_count += 1
            frame_idx = decoded_count
            timestamp_sec = round((frame_idx - 1) / fps, 4)

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
            _, full_enc = cv2.imencode(".jpg", bgr_frame, encode_param)
            frame_bytes = full_enc.tobytes()
            frame_sha256 = hashlib.sha256(frame_bytes).hexdigest()
            frame_path_str = None
            if save_frames_to_disk:
                frame_file = frames_dir / f"frame_{frame_idx:06d}.jpg"
                frame_file.write_bytes(frame_bytes)
                frame_path_str = str(frame_file)

            frame_res = ai_engine.classify_frame(
                frame_idx=frame_idx,
                timestamp_sec=timestamp_sec,
                bgr_frame=bgr_frame,
                prev_hist=prev_hist,
                thumbnail_dims=(320, 240),
            )
            frame_res.sha256_hash = frame_sha256
            frame_res.frame_path = frame_path_str

            if save_frames_to_disk and frame_res.thumbnail_data:
                thumb_file = frames_dir / f"thumb_{frame_idx:06d}.jpg"
                try:
                    b64_content = frame_res.thumbnail_data.split(",", 1)[1]
                    thumb_file.write_bytes(base64.b64decode(b64_content))
                    frame_res.thumbnail_path = str(thumb_file)
                except Exception:
                    pass

            if frame_res.classification == CLASS_SUSPICIOUS:
                suspicious_count += 1
                suspicious_timestamps.append(frame_res.timestamp_str)
                suspicious_frame_refs.append({
                    "frame_index": frame_idx,
                    "timestamp": frame_res.timestamp_str,
                    "evidence": frame_res.detection_evidence,
                    "anomaly_score": frame_res.anomaly_score,
                })
                current_suspicious_run.append(frame_res)
            elif frame_res.classification == CLASS_UNCERTAIN:
                uncertain_count += 1
                if current_suspicious_run:
                    _finalize_suspicious_segment(current_suspicious_run, suspicious_segments)
                    current_suspicious_run = []
            else:
                legitimate_count += 1
                if current_suspicious_run:
                    _finalize_suspicious_segment(current_suspicious_run, suspicious_segments)
                    current_suspicious_run = []

            timeline_markers.append({
                "frame_index": frame_idx,
                "timestamp_sec": timestamp_sec,
                "timestamp_str": frame_res.timestamp_str,
                "classification": frame_res.classification,
                "color": frame_res.color_marker,
                "anomaly_score": frame_res.anomaly_score,
            })
            frames_results.append(frame_res)
            prev_hist = ai_engine.forensic_engine.compute_color_histogram(bgr_frame)

            if progress_callback and (decoded_count % 10 == 0 or (total_expected_frames and decoded_count == total_expected_frames)):
                pct = round((decoded_count / max(1, total_expected_frames)) * 100.0, 1) if total_expected_frames else 50.0
                progress_callback({
                    "stage": "frame_classification",
                    "progress_percent": min(99.0, pct),
                    "total_frames": total_expected_frames,
                    "extracted_frames": decoded_count,
                    "classified_frames": decoded_count,
                    "legitimate_frames": legitimate_count,
                    "suspicious_frames": suspicious_count,
                    "uncertain_frames": uncertain_count,
                })
            if max_frames and decoded_count >= max_frames:
                break

        if current_suspicious_run:
            _finalize_suspicious_segment(current_suspicious_run, suspicious_segments)
        if decoded_count == 0:
            raise ValueError(f"Fail-closed: No readable visual frames could be decoded from '{video_path.name}'")

        if suspicious_count > 0:
            pct_suspicious = (suspicious_count / decoded_count) * 100.0
            peak_anomaly = max((f.anomaly_score for f in frames_results if f.classification == CLASS_SUSPICIOUS), default=75.0)
            risk_score = min(100, max(65, int(50.0 + (pct_suspicious * 1.5) + (peak_anomaly * 0.3))))
        elif uncertain_count > 0:
            risk_score = min(58, max(42, int(35.0 + (uncertain_count / decoded_count * 30.0))))
        else:
            avg_anomaly = sum(f.anomaly_score for f in frames_results) / decoded_count if decoded_count else 5.0
            risk_score = min(20, max(2, int(avg_anomaly)))

        logger.info(
            "Complete Frame Extraction SUCCESS: %d frames (legit=%d, susp=%d, uncertain=%d, risk=%d) for %s",
            decoded_count, legitimate_count, suspicious_count, uncertain_count, risk_score, video_path.name,
        )
        return {
            "total_frames_decoded": decoded_count,
            "total_expected_frames": total_expected_frames or decoded_count,
            "fps": fps,
            "width": width,
            "height": height,
            "duration_sec": round(duration_sec or (decoded_count / fps), 3),
            "legitimate_frames_count": legitimate_count,
            "suspicious_frames_count": suspicious_count,
            "uncertain_frames_count": uncertain_count,
            "failed_frames_count": failed_count,
            "risk_score": risk_score,
            "frames": frames_results,
            "timeline_markers": timeline_markers,
            "suspicious_segments": suspicious_segments,
            "suspicious_timestamps": suspicious_timestamps,
            "suspicious_frame_references": suspicious_frame_refs,
        }
    finally:
        cap.release()


def _finalize_suspicious_segment(run_frames: List[Any], out_segments: List[Dict[str, Any]]):
    """Aggregates a contiguous run of suspicious frames into a segment."""
    if not run_frames:
        return
    first = run_frames[0]
    last = run_frames[-1]
    peak_anom = max(f.anomaly_score for f in run_frames)
    reasons = list({f.detection_evidence for f in run_frames if f.detection_evidence})
    out_segments.append({
        "segment_id": len(out_segments) + 1,
        "start_frame": first.frame_index,
        "end_frame": last.frame_index,
        "start_time": first.timestamp_str,
        "end_time": last.timestamp_str,
        "frame_count": len(run_frames),
        "classification": "SUSPICIOUS",
        "color": "GREEN",
        "peak_anomaly": round(peak_anom, 1),
        "reasons": reasons[:3],
    })
