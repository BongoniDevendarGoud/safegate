"""
SafeGate — Intake & Quarantine Module (Pipeline Stage 1)
=========================================================
Performs defensive pre-screening, content validation, and secure intake:
1. Type Verification: Reads binary MAGIC BYTES using `filetype` to detect the true
   media container, preventing extension-spoofing attacks (e.g., malware.exe renamed to video.mp4).
2. Size Enforcement: Validates file size against MAX_UPLOAD_SIZE_MB to protect
   against storage and memory denial-of-service (DoS) attacks.
3. Path Traversal Defense: User-provided filenames are discarded for disk storage;
   a random cryptographic UUID4 filename is assigned instead. Path resolution
   guarantees storage remains strictly within the quarantine folder.
4. Atomic Ingestion: Writes to a temporary `.tmp` file first. If validation fails,
   the file is immediately unlinked (fail-closed cleanup).
"""

import logging
import tempfile
import uuid
from pathlib import Path, PurePosixPath
import filetype
from app.config import settings

logger = logging.getLogger(__name__)


def assert_path_within(target_path: Path, base_directory: Path) -> None:
    """
    Guarantees that target_path resolves strictly inside base_directory.
    
    Prevents path traversal attacks (e.g., using '../../' to overwrite files).
    """
    resolved_target = target_path.resolve()
    resolved_base = base_directory.resolve()
    if not resolved_target.is_relative_to(resolved_base):
        logger.error("Path traversal attempt detected: target=%s, base=%s", resolved_target, resolved_base)
        raise ValueError("Invalid target path: traversal attempt blocked")


def validate_file_type(file_path: Path) -> str:
    """
    Inspects magic bytes of a file on disk.
    
    Returns:
        MIME type string (e.g. 'video/mp4') if allowed.
        
    Raises:
        ValueError if file type is unknown or not an allowed video container.
    """
    kind = filetype.guess(str(file_path))
    if kind is None:
        raise ValueError("Could not determine file type from magic bytes. Allowed: mp4, mov, avi, mkv, webm")

    detected_mime = kind.mime.lower()
    if detected_mime not in settings.ALLOWED_MIME_TYPES:
        raise ValueError(
            f"Prohibited media type '{detected_mime}'. Allowed video formats: mp4, mov, avi, mkv, webm"
        )
    return detected_mime


def validate_file_size(file_path: Path) -> int:
    """
    Validates file size on disk against configured boundary.
    
    Returns:
        File size in bytes.
        
    Raises:
        ValueError if the file is 0 bytes or exceeds MAX_UPLOAD_SIZE_MB.
    """
    size_bytes = file_path.stat().st_size
    if size_bytes == 0:
        raise ValueError("Empty file rejected (0 bytes)")

    if size_bytes > settings.max_upload_bytes:
        mb = size_bytes / (1024 * 1024)
        raise ValueError(
            f"File size {mb:.1f} MB exceeds maximum permitted limit of {settings.MAX_UPLOAD_SIZE_MB} MB"
        )
    return size_bytes


def sanitize_filename(untrusted_filename: str) -> str:
    """
    Extracts the file extension from the user's filename and creates an
    unpredictable UUID4 hexadecimal filename.
    
    Example: 'summer_trip_../../etc.mp4' -> '8f94e2...e31.mp4'
    """
    ext = PurePosixPath(untrusted_filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Disallowed extension '{ext}'. Allowed extensions: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    return f"{uuid.uuid4().hex}{ext}"


def cleanup_file(file_path: Path) -> None:
    """
    Safely delete a file if it exists, suppressing any secondary exceptions.
    """
    try:
        if file_path.exists():
            file_path.unlink()
            logger.info("Cleaned up file: %s", file_path)
    except Exception as e:
        logger.warning("Error during file cleanup for %s: %s", file_path, e)


def save_upload(upload_bytes: bytes, original_filename: str) -> tuple:
    """
    Executes Stage 1 Intake:
    1. Rejects empty uploads immediately.
    2. Writes incoming bytes to a temporary quarantine file.
    3. Validates magic bytes (true MIME type) and file size.
    4. Atomically moves the validated file to a UUID-named destination in quarantine/.
    5. On any failure, cleans up immediately and re-raises (fail-closed).
    
    Returns:
        Tuple of (final_path: Path, stored_filename: str, original_filename: str, file_size: int)
    """
    if not upload_bytes or len(upload_bytes) == 0:
        raise ValueError("Empty file rejected (0 bytes)")

    quarantine_dir = settings.quarantine_path
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(original_filename)
    final_path = quarantine_dir / safe_name
    assert_path_within(final_path, quarantine_dir)

    temp_path: Path = None
    try:
        # Atomic write pattern: write to .tmp on the same filesystem
        with tempfile.NamedTemporaryFile(dir=str(quarantine_dir), delete=False, suffix=".tmp") as tmp:
            temp_path = Path(tmp.name)
            tmp.write(upload_bytes)

        # Stage 1 verification: magic bytes + size limits
        validate_file_type(temp_path)
        file_size = validate_file_size(temp_path)

        # Atomic rename to final UUID destination
        temp_path.rename(final_path)
        temp_path = None  # Rename succeeded, no temp file to clean up

        logger.info("Stage 1 Intake SUCCESS: Stored %s in quarantine (%d bytes)", safe_name, file_size)
        return (final_path, safe_name, original_filename, file_size)

    except Exception as e:
        # Fail-closed guarantee: destroy any orphaned fragments
        if temp_path is not None:
            cleanup_file(temp_path)
        cleanup_file(final_path)
        logger.warning("Stage 1 Intake REJECTED: %s", e)
        raise
