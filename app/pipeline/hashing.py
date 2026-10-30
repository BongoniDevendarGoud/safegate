"""
SafeGate — Exact & Perceptual Hashing (Pipeline Stages 2 & 4)
=============================================================
This module implements both exact cryptographic deduplication and fuzzy
visual deduplication against prohibited media blocklists:

1. Exact Hash (Stage 2 - SHA-256):
   - Computes a cryptographic 256-bit hash of the entire raw video payload.
   - Fast lookup (O(1)) in the `blocklist_hashes` table.
   - Match -> Immediate BLOCK.

2. Perceptual Hash (Stage 4 - pHash):
   - Computes a 64-bit DCT-based perceptual hash (`imagehash.phash`) for each
     extracted video frame.
   - Computes the Hamming distance between frame pHashes and known bad pHashes
     stored in the `blocklist_phashes` table.
   - Hamming distance <= PHASH_HAMMING_THRESHOLD -> Match -> BLOCK.

VIVA EXPLANATION:
- Cryptographic hashes (SHA-256) change completely if even one bit changes
  (Avalanche Effect). They cannot detect re-encoded, cropped, or slightly altered media.
- Perceptual hashes (pHash) generate similar bitstrings for visually similar images.
  Hamming distance counts the number of differing bits. A distance of 0 means identical
  images; a distance <= 10 indicates near-identical visual content despite compression,
  rescaling, or format conversion.
"""

import hashlib
import logging
from typing import List, Tuple, Optional
from PIL import Image
import imagehash
from sqlalchemy.orm import Session
from app.config import settings
from app.models.database import BlocklistHash, BlocklistPHash

logger = logging.getLogger(__name__)


# =============================================================================
# Stage 2: Exact Cryptographic Hashing (SHA-256)
# =============================================================================

def compute_sha256(file_bytes: bytes) -> str:
    """
    Computes standard SHA-256 hexadecimal checksum (64 characters).
    """
    return hashlib.sha256(file_bytes).hexdigest()


def check_exact_blocklist(sha256_hash: str, db: Session) -> bool:
    """
    Queries `blocklist_hashes` table for an exact SHA-256 match.
    
    Returns:
        True if the hash is blocklisted (prohibited), False otherwise.
    """
    match = db.query(BlocklistHash).filter(BlocklistHash.sha256_hash == sha256_hash).first()
    if match:
        logger.warning("Stage 2 Exact Match: Hash %s found in blocklist (source=%s)", sha256_hash, match.source)
        return True
    return False


def add_to_exact_blocklist(sha256_hash: str, db: Session, source: str = "auto-block") -> None:
    """
    Stores a newly prohibited file's SHA-256 in the blocklist table.
    """
    existing = db.query(BlocklistHash).filter(BlocklistHash.sha256_hash == sha256_hash).first()
    if not existing:
        entry = BlocklistHash(sha256_hash=sha256_hash, source=source)
        db.add(entry)
        db.commit()
        logger.info("Added SHA-256 %s to blocklist (source=%s)", sha256_hash, source)


# =============================================================================
# Stage 4: Perceptual Hashing (pHash) & Hamming Distance
# =============================================================================

def compute_frame_phash(pil_image: Image.Image) -> str:
    """
    Computes a 64-bit perceptual hash (pHash) for a single PIL image frame.
    
    Returns:
        16-character hexadecimal string representation of the 64-bit hash.
    """
    # imagehash.phash uses Discrete Cosine Transform (DCT) on low-frequency components
    ph = imagehash.phash(pil_image)
    return str(ph)


def compute_all_phashes(frames: List[Tuple[float, Image.Image]]) -> List[Tuple[float, str]]:
    """
    Computes perceptual hashes for all extracted video frames.
    
    Args:
        frames: List of (timestamp_sec, PIL.Image) tuples.
        
    Returns:
        List of (timestamp_sec, phash_hex) tuples.
    """
    results = []
    for timestamp, img in frames:
        ph_str = compute_frame_phash(img)
        results.append((timestamp, ph_str))
    return results


def hamming_distance(hex_hash1: str, hex_hash2: str) -> int:
    """
    Calculates the Hamming distance (number of bit positions where bits differ)
    between two 16-character hexadecimal pHashes.
    
    Example:
        h1 = "ffd8e4..."
        h2 = "ffd8e0..."
        distance = 2 (two bits differ)
    """
    h1 = imagehash.hex_to_hash(hex_hash1)
    h2 = imagehash.hex_to_hash(hex_hash2)
    return int(h1 - h2)  # imagehash defines subtraction as Hamming distance


def check_perceptual_blocklist(
    frame_phashes: List[Tuple[float, str]],
    db: Session,
    threshold: Optional[int] = None,
) -> Optional[Tuple[float, str, str, int]]:
    """
    Compares extracted frame pHashes against all stored prohibited pHashes.
    
    Args:
        frame_phashes: List of (timestamp, phash_hex) from the uploaded video.
        db: Database session.
        threshold: Max Hamming distance considered a match (defaults to settings.PHASH_HAMMING_THRESHOLD).
        
    Returns:
        None if no match is found.
        Tuple of (timestamp, matched_frame_phash, blocklist_phash, distance) if matched.
    """
    if threshold is None:
        threshold = settings.PHASH_HAMMING_THRESHOLD

    # Query all stored prohibited perceptual hashes
    prohibited_records = db.query(BlocklistPHash).all()
    if not prohibited_records:
        return None

    # Compare each frame against blocklist entries
    for timestamp, frame_ph in frame_phashes:
        for record in prohibited_records:
            dist = hamming_distance(frame_ph, record.phash_hex)
            if dist <= threshold:
                logger.warning(
                    "Stage 4 Perceptual Match at %.2fs: frame_phash=%s matches blocklisted=%s (distance=%d <= %d)",
                    timestamp, frame_ph, record.phash_hex, dist, threshold
                )
                return (timestamp, frame_ph, record.phash_hex, dist)

    return None


def add_to_perceptual_blocklist(phash_hexes: List[str], db: Session, source: str = "auto-block") -> int:
    """
    Inserts a list of frame pHashes from a BLOCKED video into the blocklist.
    Prevents duplicate entries.
    
    Returns:
        Number of new pHashes inserted.
    """
    existing_hashes = {r.phash_hex for r in db.query(BlocklistPHash.phash_hex).all()}
    added_count = 0

    for ph in phash_hexes:
        if ph not in existing_hashes:
            db.add(BlocklistPHash(phash_hex=ph, source=source))
            existing_hashes.add(ph)
            added_count += 1

    if added_count > 0:
        db.commit()
        logger.info("Added %d new frame pHashes to blocklist (source=%s)", added_count, source)

    return added_count
