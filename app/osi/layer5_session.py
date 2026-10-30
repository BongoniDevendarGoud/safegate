"""
SafeGate OSI Model — Layer 5: Session Layer (Auth & Audit Hash Chaining)
========================================================================
OSI MAPPING:
Layer 5 establishes, manages, and terminates communication sessions, handling authentication
and session state checkpointing.
In SafeGate, Layer 5 manages:
- Client / Moderator session authentication via API keys in constant time (`hmac.compare_digest`).
- Session isolation (preventing unauthorized cross-session access).
- Tamper-evident session audit logging (cryptographic SHA-256 hash chaining of every state transition).

VIVA EXPLANATION:
Why is authentication and the audit log mapped to Layer 5?
Because the Session Layer is responsible for establishing authorized connections between peers
and recording transactional checkpoints. SafeGate's cryptographic hash chain acts as an
immutable session log of all pipeline interactions.
"""

import hmac
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.config import settings
from app.pipeline.audit import append_audit_log, verify_audit_chain


class Layer5SessionControl:
    """
    Layer 5: Session Authentication, Privilege Verification, and Audit Chaining.
    """

    def authenticate_session(self, provided_key: Optional[str], required_role: str = "client") -> Tuple[bool, str]:
        """
        Validates the session token using constant-time comparison to prevent timing side channels.
        """
        if not provided_key:
            return False, "[Layer 5 Session Violation] Missing session authentication token."

        expected = (
            settings.ADMIN_API_KEY.encode("utf-8")
            if required_role == "admin"
            else settings.CLIENT_API_KEY.encode("utf-8")
        )
        provided = provided_key.encode("utf-8")

        if not hmac.compare_digest(provided, expected):
            return False, f"[Layer 5 Session Violation] Invalid credentials for role '{required_role}'."

        return True, f"Session authenticated successfully for role '{required_role}'."

    def log_session_event(
        self,
        action: str,
        details: Dict[str, Any],
        upload_id: Optional[str],
        db: Session,
    ):
        """Appends a cryptographic checkpoint to the Layer 5 audit hash chain."""
        return append_audit_log(action=action, details=details, upload_id=upload_id, db=db)

    def verify_session_chain(self, db: Session) -> Dict[str, Any]:
        """Verifies the integrity of the sequential session audit chain."""
        return verify_audit_chain(db)
