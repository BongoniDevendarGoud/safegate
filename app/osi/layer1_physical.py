"""
SafeGate OSI Model — Layer 1: Physical / Bitstream Layer
=========================================================
OSI MAPPING:
Layer 1 is responsible for the raw bitstream transmission and reception over
physical media. In SafeGate's software gateway, Layer 1 handles:
- Raw byte intake and chunked stream buffering.
- Zero-Trust file size boundaries (enforcing byte-length limits before allocation).
- Memory-safe spooling to avoid RAM exhaustion / Denial-of-Service.

VIVA EXPLANATION:
Why is byte intake mapped to Layer 1?
Because before analyzing syntax, codecs, or image data, the gateway operates strictly
on an unstructured sequence of raw bytes, ensuring that buffer boundaries and transfer
quotas are defended at the lowest logical abstraction.
"""

import io
from pathlib import Path
from typing import BinaryIO, Tuple
from app.config import settings


class Layer1PhysicalBitstream:
    """
    Layer 1: Raw Bitstream & Stream Buffer Enforcement.
    """

    def __init__(self, max_bytes: int = None):
        self.max_bytes = max_bytes or settings.max_upload_bytes

    def process_stream(self, stream: BinaryIO, filename_hint: str = "upload.bin") -> Tuple[bytes, int]:
        """
        Safely consumes incoming raw bitstream in 64 KB chunks up to max_bytes.

        Raises:
            ValueError: If stream is empty (0 bytes) or exceeds maximum allowable buffer.
        """
        buffer = io.BytesIO()
        total_bytes = 0
        chunk_size = 64 * 1024  # 64 KB chunks

        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > self.max_bytes:
                raise ValueError(
                    f"[Layer 1 Physical Violation] Bitstream exceeded size limit: {total_bytes} > {self.max_bytes} bytes"
                )
            buffer.write(chunk)

        if total_bytes == 0:
            raise ValueError("[Layer 1 Physical Violation] Empty bitstream: 0 bytes received.")

        raw_bytes = buffer.getvalue()
        return raw_bytes, total_bytes
