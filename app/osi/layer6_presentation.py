"""
SafeGate OSI Model — Layer 6: Presentation Layer (Syntax, MIME & Perceptual Encoding)
======================================================================================
OSI MAPPING:
Layer 6 is responsible for data representation, encoding translation, syntax validation,
and compression formats (e.g., MIME types, JPEG/MPEG encoding).
In SafeGate, Layer 6 handles:
- File signature / Magic byte syntax verification (differentiating genuine MP4/WebM from renamed binaries).
- Media normalization: Color space transcoding (OpenCV BGR to standard RGB) and spatial normalization (640x480).
- Frequency-domain encoding: 64-bit DCT perceptual hashing (pHash) and fuzzy visual deduplication.

VIVA EXPLANATION:
Why is perceptual hashing and format validation mapped to Layer 6?
Because the Presentation Layer standardizes how data is structured, represented, and translated.
Magic byte checking verifies the payload syntax, and perceptual hashing maps visual representations
into invariant frequency-domain bitstrings.
"""

import filetype
from typing import List, Tuple
from PIL import Image
from sqlalchemy.orm import Session
from app.config import settings
from app.pipeline.hashing import compute_all_phashes, check_perceptual_blocklist


class Layer6PresentationSyntax:
    """
    Layer 6: Format Syntax Verification, Color/Spatial Transcoding & Perceptual Encoding.
    """

    def verify_syntax(self, raw_bytes: bytes, original_filename: str) -> Tuple[bool, str, str]:
        """
        Validates payload syntax using binary magic bytes.

        Returns:
            (valid: bool, mime_type: str, extension: str)
        """
        kind = filetype.guess(raw_bytes)
        if kind is None:
            return False, "Could not determine file type from magic bytes. Allowed: mp4, mov, avi, mkv, webm", ""

        detected_mime = kind.mime.lower()
        if detected_mime not in settings.ALLOWED_MIME_TYPES:
            return False, f"Prohibited media type '{detected_mime}'. Allowed video formats: mp4, mov, avi, mkv, webm", ""

        return True, detected_mime, kind.extension.lower()

    def encode_perceptual_hashes(self, frames: List[Tuple[float, Image.Image]]) -> List[Tuple[float, str]]:
        """Converts extracted visual frames into 64-bit DCT perceptual hashes."""
        return compute_all_phashes(frames)

    def verify_perceptual_blocklist(
        self,
        frame_phashes: List[Tuple[float, str]],
        db: Session,
    ) -> Tuple[bool, str, str]:
        """
        Queries fuzzy blocklist for perceptual hash matches (Hamming distance <= threshold).

        Returns:
            (is_clean: bool, matched_phash: str, rationale: str)
        """
        match = check_perceptual_blocklist(frame_phashes, db)
        if match is not None:
            ts, frame_ph, block_ph, dist = match
            return False, frame_ph, f"[Layer 6 Presentation Violation] Perceptual match (pHash={frame_ph}, dist={dist})."
        return True, "", "All frame perceptual representations verified clean."
