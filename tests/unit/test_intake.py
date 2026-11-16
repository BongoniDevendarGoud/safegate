import io

import pytest

from safegate_api.errors import ErrorCode, SafeGateException
from safegate_api.intake import (
    MediaMetadata,
    sniff_mime_type,
    validate_and_hash_stream,
)


def test_sniff_mime_type_jpeg() -> None:
    """Verify JPEG magic bytes detection."""
    header = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    assert sniff_mime_type(header) == "image/jpeg"


def test_sniff_mime_type_png() -> None:
    """Verify PNG magic bytes detection."""
    header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    assert sniff_mime_type(header) == "image/png"


def test_sniff_mime_type_webp() -> None:
    """Verify WebP magic bytes detection."""
    header = b"RIFF\x20\x00\x00\x00WEBPVP8 \x14\x00\x00\x00"
    assert sniff_mime_type(header) == "image/webp"


def test_sniff_mime_type_mp4() -> None:
    """Verify MP4 magic bytes detection (box header with 'ftyp')."""
    header = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2mp41"
    assert sniff_mime_type(header) == "video/mp4"


def test_sniff_mime_type_webm() -> None:
    """Verify WebM magic bytes detection."""
    header = b"\x1a\x45\xdf\xa3\x9f\x42\x86\x81\x01\x42\xf7\x81\x01\x42\xf2\x81"
    assert sniff_mime_type(header) == "video/webm"


def test_sniff_mime_type_unsupported() -> None:
    """Verify unknown header raises 415 UNSUPPORTED_MEDIA_TYPE."""
    invalid_header = (
        b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"  # Windows PE executable
    )
    with pytest.raises(SafeGateException) as exc_info:
        sniff_mime_type(invalid_header)
    assert exc_info.value.code == ErrorCode.UNSUPPORTED_MEDIA_TYPE
    assert exc_info.value.status_code == 415


def test_validate_and_hash_stream_valid() -> None:
    """Verify stream validation, hashing, and metadata generation."""
    png_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + (b"\x00" * 50)
    stream = io.BytesIO(png_data)

    meta = validate_and_hash_stream(stream=stream, max_size_bytes=1024)
    assert isinstance(meta, MediaMetadata)
    assert meta.mime_type == "image/png"
    assert meta.size_bytes == len(png_data)
    assert not meta.is_video
    assert len(meta.sha256_hash) == 64


def test_validate_and_hash_stream_exceeds_size() -> None:
    """Verify file exceeding size limit raises 413 PAYLOAD_TOO_LARGE."""
    fake_data = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 200)
    stream = io.BytesIO(fake_data)

    with pytest.raises(SafeGateException) as exc_info:
        validate_and_hash_stream(stream=stream, max_size_bytes=50)
    assert exc_info.value.code == ErrorCode.PAYLOAD_TOO_LARGE
    assert exc_info.value.status_code == 413
