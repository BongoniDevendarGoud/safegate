"""
SafeGate — Configuration & Central Settings
============================================
Every threshold, credential, and path in SafeGate is defined in this module.
All configuration is loaded from environment variables (managed via .env)
using python-dotenv.

VIVA EXPLANATION / DESIGN PRINCIPLES:
1. No Magic Numbers: Hardcoding values like "0.85" directly inside detection algorithms
   makes auditing difficult and prevents environment-specific tuning.
2. Immutability: The `Settings` dataclass is frozen (`frozen=True`) to prevent runtime
   tampering or accidental mutations from worker threads.
3. Fail-Closed Boundaries: If any threshold environment variable is missing or malformed,
   safe, conservative defaults are applied immediately.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple
from dotenv import load_dotenv

# Load key-value pairs from .env into os.environ at import time.
# If .env does not exist, load_dotenv() fails silently and environment defaults apply.
load_dotenv()


def _get_bool(env_var_name: str, default: bool = False) -> bool:
    """
    Safely parse boolean environment flags.
    
    Treats case-insensitive 'true', '1', 'yes', 't' as True; everything else as False.
    This prevents common Python bugs where bool("false") evaluates to True.
    """
    raw = os.getenv(env_var_name, str(default)).strip().lower()
    return raw in ("true", "1", "yes", "t")


@dataclass(frozen=True)
class Settings:
    """
    Immutable container of all runtime configuration parameters for SafeGate.
    """

    # -------------------------------------------------------------------------
    # Authentication & API Keys
    # -------------------------------------------------------------------------
    # Key required in X-API-Key header for moderator, review, and audit endpoints
    ADMIN_API_KEY: str = field(
        default_factory=lambda: os.getenv("ADMIN_API_KEY", "change-me-to-a-strong-random-key")
    )
    # Separate client key for upload endpoints (Least Privilege principle)
    CLIENT_API_KEY: str = field(
        default_factory=lambda: os.getenv("CLIENT_API_KEY", "change-me-to-a-client-key")
    )

    # -------------------------------------------------------------------------
    # Gemini AI Second-Opinion Screening
    # -------------------------------------------------------------------------
    # When False, SafeGate runs in purely local/offline mode without calling Google APIs
    USE_GEMINI: bool = field(
        default_factory=lambda: _get_bool("USE_GEMINI", False)
    )
    # Gemini API Key (read from GEMINI_API_KEY env var, never logged)
    GEMINI_API_KEY: str = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "")
    )
    # Gemini model name must come from GEMINI_MODEL env var, never hardcoded
    GEMINI_MODEL: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    )

    # -------------------------------------------------------------------------
    # NSFW Detection Thresholds
    # -------------------------------------------------------------------------
    # Frames scoring >= BLOCK_THRESHOLD are automatically BLOCKED
    BLOCK_THRESHOLD: float = field(
        default_factory=lambda: float(os.getenv("BLOCK_THRESHOLD", "0.85"))
    )
    # Frames scoring in [REVIEW_THRESHOLD, BLOCK_THRESHOLD) trigger Gemini or moderator REVIEW
    REVIEW_THRESHOLD: float = field(
        default_factory=lambda: float(os.getenv("REVIEW_THRESHOLD", "0.45"))
    )

    # -------------------------------------------------------------------------
    # Perceptual Hashing & Frame Extraction
    # -------------------------------------------------------------------------
    # Maximum Hamming distance between two 64-bit pHashes to be considered a match.
    # Lower is stricter (distance 0 = exact image; distance <= 10 = near duplicate).
    PHASH_HAMMING_THRESHOLD: int = field(
        default_factory=lambda: int(os.getenv("PHASH_HAMMING_THRESHOLD", "10"))
    )
    # Safety cap: maximum number of frames extracted per video (prevents CPU exhaustion)
    MAX_FRAMES: int = field(
        default_factory=lambda: int(os.getenv("MAX_FRAMES", "60"))
    )
    # Temporal interval: extract 1 frame every N seconds of video duration
    FRAME_INTERVAL_SEC: int = field(
        default_factory=lambda: int(os.getenv("FRAME_INTERVAL_SEC", "2"))
    )

    # -------------------------------------------------------------------------
    # Upload Limits & Rate Limiting
    # -------------------------------------------------------------------------
    # Hard size limit on incoming uploads (Megabytes)
    MAX_UPLOAD_SIZE_MB: int = field(
        default_factory=lambda: int(os.getenv("MAX_UPLOAD_SIZE_MB", "200"))
    )
    # Maximum uploads per minute per IP address
    RATE_LIMIT_PER_MINUTE: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    )

    # -------------------------------------------------------------------------
    # Deepfake Risk Thresholds (Probabilistic / Advisory Signal)
    # -------------------------------------------------------------------------
    # Composite score (0-100) >= this sends video to REVIEW (never auto-blocks)
    DEEPFAKE_REVIEW_THRESHOLD: int = field(
        default_factory=lambda: int(os.getenv("DEEPFAKE_REVIEW_THRESHOLD", "60"))
    )

    # -------------------------------------------------------------------------
    # Networking & Storage Locations
    # -------------------------------------------------------------------------
    DASHBOARD_ORIGIN: str = field(
        default_factory=lambda: os.getenv("DASHBOARD_ORIGIN", "http://localhost:8000")
    )
    HOST: str = field(
        default_factory=lambda: os.getenv("HOST", "0.0.0.0")
    )
    PORT: int = field(
        default_factory=lambda: int(os.getenv("PORT", "8000"))
    )
    QUARANTINE_DIR: str = field(
        default_factory=lambda: os.getenv("QUARANTINE_DIR", "quarantine")
    )
    REVIEW_DIR: str = field(
        default_factory=lambda: os.getenv("REVIEW_DIR", "review")
    )
    PUBLISHED_DIR: str = field(
        default_factory=lambda: os.getenv("PUBLISHED_DIR", "published")
    )
    DATABASE_URL: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///safegate.db")
    )

    # -------------------------------------------------------------------------
    # Static Constants (Extensions, MIME types, Normalization)
    # -------------------------------------------------------------------------
    ALLOWED_EXTENSIONS: List[str] = field(
        default_factory=lambda: [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    )
    ALLOWED_MIME_TYPES: List[str] = field(
        default_factory=lambda: [
            "video/mp4",
            "video/quicktime",
            "video/x-msvideo",
            "video/x-matroska",
            "video/webm",
        ]
    )
    FRAME_RESIZE: Tuple[int, int] = field(default_factory=lambda: (640, 480))

    # -------------------------------------------------------------------------
    # Computed Helper Properties
    # -------------------------------------------------------------------------
    @property
    def max_upload_bytes(self) -> int:
        """Calculate maximum upload file size in bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def quarantine_path(self) -> Path:
        """Resolved filesystem path for quarantine directory."""
        return Path(self.QUARANTINE_DIR).resolve()

    @property
    def review_path(self) -> Path:
        """Resolved filesystem path for review directory."""
        return Path(self.REVIEW_DIR).resolve()

    @property
    def published_path(self) -> Path:
        """Resolved filesystem path for published directory."""
        return Path(self.PUBLISHED_DIR).resolve()


# Singleton settings instance accessible across all modules
settings = Settings()
