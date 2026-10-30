"""
SafeGate OSI Model — Layer 4: Transport Layer (Integrity & Exact Hashes)
========================================================================
OSI MAPPING:
Layer 4 guarantees end-to-end data integrity via transport checksums (like TCP/UDP checksums).
In SafeGate, Layer 4 provides:
- Cryptographic payload integrity computation (SHA-256 checksum).
- Transport-layer deduplication and exact-match blocklist query ($O(1)$).
- Immediate blocking if the transport checksum matches a known prohibited media digest.

VIVA EXPLANATION:
Why is exact hashing mapped to Layer 4?
Because Layer 4 in the OSI model is responsible for end-to-end checksum verification.
If the transport checksum reveals that the exact payload is malicious, it can be
discarded immediately at the transport layer before higher layers waste CPU decoding it.
"""

from typing import Tuple
from sqlalchemy.orm import Session
from app.pipeline.hashing import compute_sha256, check_exact_blocklist, add_to_exact_blocklist


class Layer4TransportIntegrity:
    """
    Layer 4: Payload Integrity & Cryptographic Checksum Matching.
    """

    def compute_checksum(self, payload_bytes: bytes) -> str:
        """Computes deterministic 256-bit SHA-256 transport checksum."""
        return compute_sha256(payload_bytes)

    def verify_transport_blocklist(self, sha256_hash: str, db: Session) -> Tuple[bool, str]:
        """
        Queries exact-match blocklist for transport checksum.

        Returns:
            (is_clean: bool, rationale: str)
        """
        is_blocked = check_exact_blocklist(sha256_hash, db)
        if is_blocked:
            return False, f"[Layer 4 Transport Violation] Checksum {sha256_hash[:16]}... matched in exact blocklist."
        return True, f"Transport checksum {sha256_hash[:16]}... verified clean."
