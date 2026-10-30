"""
SafeGate OSI Model — Layer 7: Application / AI Policy Layer
============================================================
OSI MAPPING:
Layer 7 directly interfaces with end-user applications and high-level decision logic.
In SafeGate, Layer 7 represents the cognitive intelligence and governance core:
- Deep Learning Vision Model: Local offline classification via Vision Transformers (`Falconsai/nsfw_image_detection`).
- Cloud Multimodal Intelligence: Gemini second opinion for borderline confidence bounds $[0.45, 0.85)$.
- Synthetic Manipulation Forensics: Deepfake advisory scoring (0-100) combining temporal flicker, sharpness variance, and container metadata.
- Policy Decision Engine: Synthesizes all lower-layer and higher-layer signals into final verdicts: `ALLOW`, `REVIEW`, or `BLOCK`.

VIVA EXPLANATION:
Why is AI inference and policy enforcement mapped to Layer 7?
Because the Application Layer contains the business logic and high-level decision-making
rules that govern the application. It evaluates semantic meaning, policy compliance,
and user safety.
"""

from pathlib import Path
from typing import List, Tuple, Dict, Any
from PIL import Image
from app.pipeline.nsfw_detector import score_frames
from app.pipeline.gemini_opinion import query_gemini_second_opinion
from app.pipeline.deepfake_detector import calculate_deepfake_risk
from app.pipeline.decision import evaluate_signals, ScreeningSignals, DecisionResult


class Layer7ApplicationPolicy:
    """
    Layer 7: Cognitive AI Screening, Deepfake Risk Analysis & Policy Decision Engine.
    """

    def classify_nsfw_frames(self, frames: List[Tuple[float, Image.Image]]) -> Tuple[float, float, List[Dict[str, Any]]]:
        """Runs local Vision Transformer across sampled frames."""
        return score_frames(frames)

    def request_cloud_opinion(
        self,
        frame_image: Image.Image,
        timestamp: float,
    ) -> Dict[str, Any]:
        """Consults Gemini multimodal API strictly for borderline scores."""
        return query_gemini_second_opinion(frame_image, timestamp)

    def evaluate_synthetic_manipulation(
        self,
        video_path: Path,
        frames: List[Tuple[float, Image.Image]],
    ) -> Tuple[int, List[str]]:
        """Computes composite deepfake risk score (0-100) and rationale list."""
        return calculate_deepfake_risk(video_path, frames)

    def execute_policy_decision(self, signals: ScreeningSignals) -> DecisionResult:
        """
        Synthesizes signals from all 7 layers into the final fail-closed verdict.

        Returns:
            DecisionResult(verdict: "ALLOW" | "REVIEW" | "BLOCK", explanation: str, triggered_stage: str)
        """
        return evaluate_signals(signals)
