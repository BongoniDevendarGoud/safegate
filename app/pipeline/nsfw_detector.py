"""
SafeGate — Local NSFW Screening Model (Pipeline Stage 5)
=========================================================
Uses Hugging Face Transformers with the `Falconsai/nsfw_image_detection`
model (a Vision Transformer fine-tuned to classify images as 'normal' or 'nsfw').

HOW IT WORKS:
1. Lazy Singleton Loader: Model weights (~300MB) are loaded into memory once on
   the first invocation to avoid cold-start overhead per upload.
2. Per-Frame Inference: Iterates through each extracted PIL frame, passes it to the
   classifier pipeline, and extracts the confidence probability for the 'nsfw' label.
3. Worst-Case Tracking: Records the maximum NSFW confidence and the exact video
   timestamp (in seconds) where it occurred.

FAIL-CLOSED DESIGN:
- If transformers or torch is unavailable or fails to initialize, the detector raises
  a RuntimeError. The orchestrator catches this and assigns a verdict of REVIEW.
- If a frame is unreadable or causes an inference exception, it fails closed to REVIEW.

TESTING MODE:
- Supports `SAFEGATE_TEST_MODE=true` or lowered thresholds (e.g., `BLOCK_THRESHOLD=0.01`)
  to verify the BLOCK decision pathway using safe, synthetic videos without requiring
  explicit imagery.
"""

import logging
import os
from typing import List, Tuple, Optional
from PIL import Image
from app.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton holding the loaded HuggingFace pipeline
_classifier = None
_model_load_attempted = False
_model_load_error: Optional[str] = None


def get_nsfw_classifier():
    """
    Retrieves the cached transformers image-classification pipeline,
    or lazily initializes it on first access.
    """
    global _classifier, _model_load_attempted, _model_load_error

    if _classifier is not None:
        return _classifier

    if _model_load_attempted and _model_load_error:
        raise RuntimeError(f"NSFW model unavailable: {_model_load_error}")

    _model_load_attempted = True

    # Check for test mode mock to allow unit tests without 300MB download
    if os.getenv("SAFEGATE_MOCK_MODEL", "false").lower() in ("true", "1", "yes"):
        logger.info("SAFEGATE_MOCK_MODEL active: using mock classifier")
        def _mock_pipeline(img):
            # Returns fixed safe score (0.02) unless mock explicit score is set
            score = float(os.getenv("SAFEGATE_MOCK_NSFW_SCORE", "0.02"))
            return [{"label": "nsfw", "score": score}, {"label": "normal", "score": 1.0 - score}]
        _classifier = _mock_pipeline
        return _classifier

    try:
        from transformers import pipeline
        import torch

        model_name = "Falconsai/nsfw_image_detection"
        device = 0 if torch.cuda.is_available() else -1
        logger.info("Loading NSFW model '%s' (device=%s)...", model_name, "GPU" if device == 0 else "CPU")

        _classifier = pipeline(
            "image-classification",
            model=model_name,
            device=device,
        )
        logger.info("NSFW model '%s' loaded successfully.", model_name)
        return _classifier

    except Exception as e:
        _model_load_error = str(e)
        logger.error("Failed to load NSFW model '%s': %s", "Falconsai/nsfw_image_detection", e)
        raise RuntimeError(f"Failed to initialize local NSFW model: {e}") from e


def score_frames(frames: List[Tuple[float, Image.Image]]) -> Tuple[float, float, List[dict]]:
    """
    Evaluates a sequence of video frames against the NSFW classification model.

    Args:
        frames: List of (timestamp_in_seconds, PIL.Image) tuples.

    Returns:
        Tuple of:
            - worst_score (float): Peak confidence score for 'nsfw' (0.0 to 1.0)
            - worst_timestamp (float): Video timestamp of worst frame
            - all_scores (list of dicts): Detailed log [{timestamp, score}]
    """
    if not frames:
        raise ValueError("Cannot score empty frame sequence")

    classifier = get_nsfw_classifier()

    worst_score = 0.0
    worst_timestamp = 0.0
    all_scores = []

    for timestamp, frame_img in frames:
        try:
            # Hugging Face image-classification returns a list of dictionaries:
            # [{'label': 'nsfw', 'score': 0.98}, {'label': 'normal', 'score': 0.02}]
            predictions = classifier(frame_img)
            nsfw_conf = 0.0
            for pred in predictions:
                if pred.get("label", "").lower() == "nsfw":
                    nsfw_conf = float(pred.get("score", 0.0))
                    break

            all_scores.append({"timestamp": timestamp, "score": nsfw_conf})

            if nsfw_conf > worst_score:
                worst_score = nsfw_conf
                worst_timestamp = timestamp

        except Exception as exc:
            logger.error("Error during inference on frame at %.2fs: %s", timestamp, exc)
            # Fail-closed: re-raise so orchestrator treats this as a REVIEW event
            raise RuntimeError(f"NSFW model inference failure at {timestamp}s: {exc}") from exc

    logger.info(
        "Stage 5 NSFW Screening Complete: worst_score=%.4f at %.2fs (evaluated %d frames)",
        worst_score, worst_timestamp, len(frames)
    )

    return (worst_score, worst_timestamp, all_scores)
