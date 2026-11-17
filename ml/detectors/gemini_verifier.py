"""
SafeGate Gemini Multimodal AI Verification Branch.
Integrates Google Gemini 2.0 / 1.5 Flash to perform vision reasoning on candidate video frames.
Operates as an auxiliary high-confidence detector when GEMINI_API_KEY is configured.
"""

from __future__ import annotations

import io
import json
import os
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class GeminiVerificationResult:
    available: bool
    is_manipulated: bool
    manipulation_score: float  # [0.0, 1.0]
    explanation: str
    detected_artifacts: list[str]


class GeminiMultimodalVerifier:
    """
    Leverages Gemini Multimodal API to detect AI deepfakes, face swaps, morphs, and splicing.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception:
                self.client = None

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    def analyze_candidate_frames(self, frames: list[np.ndarray]) -> GeminiVerificationResult:
        """
        Sends sampled candidate frames to Gemini for deepfake and forensic manipulation analysis.
        """
        if not self.is_configured or not frames:
            return GeminiVerificationResult(
                available=False,
                is_manipulated=False,
                manipulation_score=0.0,
                explanation="Gemini API not configured or no frames supplied.",
                detected_artifacts=[],
            )

        try:
            from PIL import Image

            pil_images = []
            for frame in frames[:6]:  # Limit to 6 keyframes for fast latency
                rgb = frame if frame.shape[2] == 3 else cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_images.append(Image.fromarray(rgb))

            prompt = (
                "You are an expert digital media forensics and deepfake detection system. "
                "Analyze these video frames for any evidence of: "
                "1. Digital manipulation, face swapping, or facial morphing. "
                "2. Video splicing, inserted foreign clips, or sudden scene/lighting discontinuity. "
                "3. AI-generated diffusion artifacts, unnatural textures, or warped boundaries. "
                "Reply ONLY in valid JSON matching this exact schema: "
                "{\n"
                '  "is_manipulated": true/false,\n'
                '  "manipulation_score": 0.0 to 1.0,\n'
                '  "explanation": "concise explanation of findings",\n'
                '  "detected_artifacts": ["artifact1", "artifact2"]\n'
                "}"
            )

            response = self.client.models.generate_content(
                model=os.environ.get("GEMINI_MODEL", "gemini-3.5-flash"),
                contents=[prompt, *pil_images],
            )

            text = response.text.strip()
            # Clean possible markdown block
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text.strip())

            return GeminiVerificationResult(
                available=True,
                is_manipulated=bool(data.get("is_manipulated", False)),
                manipulation_score=float(data.get("manipulation_score", 0.0)),
                explanation=str(data.get("explanation", "Forensic inspection complete.")),
                detected_artifacts=list(data.get("detected_artifacts", [])),
            )
        except Exception as exc:
            return GeminiVerificationResult(
                available=False,
                is_manipulated=False,
                manipulation_score=0.0,
                explanation=f"Gemini API inference error: {exc}",
                detected_artifacts=[],
            )
