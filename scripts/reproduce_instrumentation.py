"""
STEP 1: REPRODUCE AND INSTRUMENT
Debug script to inspect exact outputs across all branches, fusion, temporal confirmation, and policy.
"""

from __future__ import annotations

import json
from pathlib import Path
import cv2
import numpy as np

from ml.detectors.pipeline import MultiBranchPipeline
from ml.fusion.calibrator import ScoreCalibrator
from ml.fusion.temporal_confirmation import TemporalConfirmationEngine
from safegate_api.config import settings
from safegate_worker.extractor import extract_media_frames
from safegate_worker.policy import ContentPolicyEngine


def instrument_media(media_path: Path, label: str) -> None:
    print(f"\n=======================================================")
    print(f"INSTRUMENTATION RUN: [{label}] -> {media_path.name}")
    print(f"=======================================================")

    pipeline = MultiBranchPipeline()
    calibrator = ScoreCalibrator()
    confirmation_engine = TemporalConfirmationEngine(thresholds=settings.thresholds)
    policy_engine = ContentPolicyEngine()

    # Model & Detector Metadata
    # Inspect each detector branch for model files, weights, and versions
    print("\n--- MODEL & DETECTOR REGISTRY INFO ---")
    print(f"Detector Architecture: MultiBranchPipeline")
    print(f"Spatial Branch Type: {type(pipeline.spatial_detector).__name__} (Haar Cascade: {pipeline.spatial_detector.face_cascade is not None})")
    print(f"Frequency Branch Type: {type(pipeline.frequency_detector).__name__} (FFT Azimuthal Integration)")
    print(f"Temporal Branch Type: {type(pipeline.temporal_detector).__name__} (Inter-frame Disparity)")
    print(f"Sensitive Branch Type: {type(pipeline.sensitive_classifier).__name__} (Color Space Loci Heuristic)")
    print(f"Model Checksum: NONE (No PyTorch/ONNX/TensorFlow checkpoints loaded)")
    print(f"Model Version: '0.1.0-heuristic-baseline'")
    print(f"Thresholds Config:")
    print(f"  Deepfake RED block: {settings.thresholds.deepfake_manipulation_score.red_block_threshold}")
    print(f"  Deepfake YELLOW review: {settings.thresholds.deepfake_manipulation_score.yellow_review_threshold}")
    print(f"  Sensitive YELLOW review: {settings.thresholds.sensitive_content_score.yellow_review_threshold}")
    print(f"  Uncertainty YELLOW review: {settings.thresholds.uncertainty_score.yellow_review_threshold}")

    frames = list(extract_media_frames(media_path))
    print(f"Total Decoded Frames: {len(frames)}")

    fused_frames = []
    is_single = len(frames) <= 1

    print("\n--- PER-FRAME BRANCH SCORES (First 10 frames) ---")
    for i, fd in enumerate(frames):
        raw_res = pipeline.process_frame(fd.rgb_array, fd.frame_index, fd.timestamp_ms)
        fused = calibrator.calibrate_and_fuse(raw_res, is_single_frame=is_single)
        fused_frames.append(fused)

        if i < 10:
            print(
                f"Frame {i:03d} (t={fd.timestamp_ms}ms) | "
                f"Spatial: {raw_res.spatial.manipulation_score:.4f} (face={raw_res.spatial.face_detected}) | "
                f"Freq: {raw_res.frequency.manipulation_score:.4f} (grid={raw_res.frequency.grid_artifact_detected}) | "
                f"Temp: {raw_res.temporal.anomaly_score:.4f} | "
                f"Sens: {raw_res.sensitive.sensitive_score:.4f} | "
                f"Fused Deepfake: {fused.manipulation_score:.4f} | "
                f"Uncertainty: {fused.uncertainty_score:.4f}"
            )

    # Temporal confirmation & color assignment
    verdicts = confirmation_engine.evaluate_sequence(fused_frames)
    decision = policy_engine.evaluate(verdicts)

    color_counts = {"RED": 0, "YELLOW": 0, "GREEN": 0}
    for v in verdicts:
        color_counts[v.color] += 1

    print("\n--- AGGREGATE DECISION & POLICY RESOLUTION ---")
    print(f"Assigned Colors: {color_counts}")
    print(f"Final Decision: {decision.verdict}")
    print(f"Decision Reason: {decision.summary_reason}")
    print(f"Allow Confirmed: {decision.verdict == 'ALLOW'}")


def main():
    root = Path(__file__).resolve().parent.parent

    # (a) scenario2_deepfake.mp4
    deepfake_path = root / "samples" / "scenario2_deepfake.mp4"

    # (b) normal real video
    legit_path = root / "samples" / "scenario1_legitimate.mp4"

    # (c) test image
    test_img_path = root / "samples" / "test_image.jpg"
    if not test_img_path.exists():
        # Create a standard synthetic RGB image
        img = np.zeros((300, 300, 3), dtype=np.uint8)
        img[:, :] = (120, 160, 200) # Natural sky-blue tint
        cv2.imwrite(str(test_img_path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

    instrument_media(deepfake_path, "Scenario 2: Synthetic Deepfake")
    instrument_media(legit_path, "Scenario 1: Legitimate Normal Video")
    instrument_media(test_img_path, "Test Image: Static Capture")


if __name__ == "__main__":
    main()
