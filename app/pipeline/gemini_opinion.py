"""
SafeGate — Gemini Second Opinion Screening (Pipeline Stage 6)
==============================================================
Provides secondary multimodal AI evaluation for BORDERLINE frames only.

SECURITY & ARCHITECTURAL RULES:
1. Borderline Only: Never invokes Gemini for media already determined to be
   clearly safe (NSFW < REVIEW_THRESHOLD) or clearly explicit (NSFW >= BLOCK_THRESHOLD).
   This conserves API quota and minimizes external network transmission.
2. Offline Compatibility: Controlled by the `USE_GEMINI` environment variable.
   When False, this stage is bypassed gracefully and borderline media remains
   in REVIEW (fail-closed).
3. Dynamic Model Config: Model name is loaded strictly from the `GEMINI_MODEL`
   environment variable, never hardcoded in source.
4. Strict JSON Enforcement: Requests structured JSON output matching:
   {"explicit": bool, "confidence": float, "reason": str}
5. Fail-Closed Error Handling: Safety policy refusals, HTTP 429 rate limits,
   network timeouts, or malformed JSON payloads are treated as "uncertain"
   (confidence < 0.5, explicit=False, routed to human moderator).
"""

import io
import json
import logging
import os
from typing import Optional, Dict, Any
from PIL import Image
from app.config import settings

logger = logging.getLogger(__name__)


def is_borderline(nsfw_score: float) -> bool:
    """
    Returns True if the local NSFW score falls in the borderline review range
    [REVIEW_THRESHOLD, BLOCK_THRESHOLD).
    """
    return settings.REVIEW_THRESHOLD <= nsfw_score < settings.BLOCK_THRESHOLD


def query_gemini_second_opinion(
    frame_image: Image.Image,
    timestamp: float,
) -> Dict[str, Any]:
    """
    Sends a borderline image frame to Google Gemini for content safety verification.

    Args:
        frame_image: The PIL Image frame flagged as borderline.
        timestamp: Video offset in seconds where the frame occurred.

    Returns:
        Dictionary with keys:
            - explicit (bool): True if explicitly adult/pornographic
            - confidence (float): 0.0 to 1.0
            - reason (str): Concise explanation
            - raw_response (str): String representation for audit logs
    """
    # Check for unit testing mock override first
    mock_resp = os.getenv("SAFEGATE_MOCK_GEMINI_RESPONSE")
    if mock_resp:
        logger.info("Stage 6 Gemini: Using mock response: %s", mock_resp)
        try:
            parsed = json.loads(mock_resp)
            return {
                "explicit": bool(parsed.get("explicit", False)),
                "confidence": float(parsed.get("confidence", 0.0)),
                "reason": str(parsed.get("reason", "Mock response")),
                "raw_response": mock_resp,
            }
        except Exception as e:
            logger.warning("Mock Gemini JSON parse failed: %s", e)
            return {
                "explicit": False,
                "confidence": 0.0,
                "reason": f"Malformed mock response: {e}",
                "raw_response": mock_resp,
            }

    # 1. Verify offline/online gate
    if not settings.USE_GEMINI:
        logger.info("Stage 6 Gemini: USE_GEMINI=false; skipping cloud second opinion (offline mode).")
        return {
            "explicit": False,
            "confidence": 0.0,
            "reason": "Gemini second opinion disabled (USE_GEMINI=false). Routed to moderator.",
            "raw_response": "SKIPPED_OFFLINE",
        }

    # 2. Check API key presence
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your-gemini-api-key-here":
        logger.warning("Stage 6 Gemini: Missing or placeholder GEMINI_API_KEY. Fail-closed to uncertain.")
        return {
            "explicit": False,
            "confidence": 0.0,
            "reason": "GEMINI_API_KEY not configured. Fail-closed to human review.",
            "raw_response": "MISSING_KEY",
        }

    # 3. Format prompt requesting strict JSON
    prompt = (
        "You are an automated content-safety classifier. "
        "Examine this video frame and determine if it depicts sexually explicit, "
        "pornographic, or 18+ adult content.\n"
        "Respond ONLY with a valid JSON object in this exact schema without markdown backticks:\n"
        '{"explicit": true or false, "confidence": float between 0.0 and 1.0, "reason": "brief plain text explanation"}\n'
        "If you are uncertain or the media is ambiguous, set explicit to false and confidence below 0.5."
    )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        model_name = settings.GEMINI_MODEL

        # Convert PIL image to JPEG bytes buffer
        img_buffer = io.BytesIO()
        frame_image.save(img_buffer, format="JPEG", quality=85)
        jpeg_bytes = img_buffer.getvalue()

        image_part = types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg")

        logger.info(
            "Stage 6 Gemini: Dispatching second-opinion query to model '%s' (frame at %.2fs)...",
            model_name, timestamp
        )

        response = client.models.generate_content(
            model=model_name,
            contents=[prompt, image_part],
        )

        raw_text = response.text.strip()
        logger.info("Stage 6 Gemini Raw Response: %s", raw_text)

        # Clean potential markdown wrapping (e.g. ```json ... ```)
        cleaned = raw_text
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        data = json.loads(cleaned)
        explicit = bool(data.get("explicit", False))
        confidence = float(data.get("confidence", 0.0))
        reason = str(data.get("reason", "No reason provided by model."))

        return {
            "explicit": explicit,
            "confidence": max(0.0, min(1.0, confidence)),
            "reason": reason,
            "raw_response": raw_text,
        }

    except Exception as exc:
        # Fail-closed guarantee: any API error, 429 rate limit, timeout, or safety block
        # is logged and returned as uncertain (explicit=False, confidence=0.0)
        logger.warning(
            "Stage 6 Gemini Exception: %s. Applying fail-closed uncertain verdict.",
            exc
        )
        return {
            "explicit": False,
            "confidence": 0.0,
            "reason": f"Gemini query failed or timed out ({type(exc).__name__}). Routed to human moderator.",
            "raw_response": f"ERROR: {exc}",
        }
