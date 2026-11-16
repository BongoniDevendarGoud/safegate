"""
SafeGate Media Intake & Binary Sanitization.
Validates file headers, magic bytes, container integrity, and computes SHA-256.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import BinaryIO

from safegate_api.errors import (
    ErrorCode,
    MediaDecodeError,
    SafeGateException,
)

# Known magic byte signatures
MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF", b"WEBP"],  # Checked via chunk inspection
    "video/mp4": [b"ftyp"],  # Usually offset by 4 bytes: [size][ftyp]
    "video/webm": [b"\x1a\x45\xdf\xa3"],  # Matroska / WebM EBML ID
    "video/quicktime": [b"ftypqt  ", b"moov"],
}

SUPPORTED_MIME_TYPES = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "image/jpeg",
    "image/png",
    "image/webp",
}


@dataclass(frozen=True)
class MediaMetadata:
    mime_type: str
    sha256_hash: str
    size_bytes: int
    is_video: bool


def sniff_mime_type(header: bytes) -> str:
    """
    Inspects the initial binary header bytes to determine authentic MIME type.
    Rejects spoofed file extensions.
    """
    if len(header) < 16:
        raise MediaDecodeError("File header is too short for magic byte inspection.")

    # JPEG check
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    # PNG check
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    # WebP check (RIFF....WEBP)
    if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
        return "image/webp"

    # WebM check (EBML header)
    if header.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"

    # MP4 check (box header: 4 bytes size, then 'ftyp')
    if len(header) >= 8 and header[4:8] == b"ftyp":
        # Additional brand checks (e.g. isom, mp42, qt)
        return "video/mp4"

    # QuickTime MOV check
    if len(header) >= 8 and (
        header[4:8] == b"moov" or header[4:8] == b"free" or header[4:8] == b"mdat"
    ):
        return "video/quicktime"

    raise SafeGateException(
        message="Unsupported or invalid media format",
        code=ErrorCode.UNSUPPORTED_MEDIA_TYPE,
        status_code=415,
        detail=f"Binary header '{header[:8].hex()}' does not match any supported media signature.",
    )


def validate_and_hash_stream(
    stream: BinaryIO,
    max_size_bytes: int,
    chunk_size: int = 65536,
) -> MediaMetadata:
    """
    Streams file chunks, validates magic bytes on first chunk, checks size limit,
    and calculates cryptographic SHA-256 hash in a single pass.
    """
    hasher = hashlib.sha256()
    total_size = 0
    header_bytes = b""
    first_chunk = True
    mime_type = ""

    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break

        total_size += len(chunk)
        if total_size > max_size_bytes:
            raise SafeGateException(
                message="File size exceeds policy threshold",
                code=ErrorCode.PAYLOAD_TOO_LARGE,
                status_code=413,
                detail=f"Uploaded payload size ({total_size} bytes) exceeds maximum limit ({max_size_bytes} bytes).",
            )

        if first_chunk:
            header_bytes = chunk[:64]
            mime_type = sniff_mime_type(header_bytes)
            first_chunk = False

        hasher.update(chunk)

    if total_size == 0:
        raise MediaDecodeError("Uploaded stream is empty (0 bytes).")

    is_video = mime_type.startswith("video/")

    return MediaMetadata(
        mime_type=mime_type,
        sha256_hash=hasher.hexdigest(),
        size_bytes=total_size,
        is_video=is_video,
    )
