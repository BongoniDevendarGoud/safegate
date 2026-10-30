"""
SafeGate — Authentication & Authorization Module
=================================================
Implements API-key authentication using HTTP headers (`X-API-Key`):
1. `CLIENT_API_KEY`: Required for public upload endpoints (`/api/upload`).
2. `ADMIN_API_KEY`: Required for privileged moderator and audit endpoints
   (`/api/audit/*`, `/api/review/*`).

SECURITY PRINCIPLES:
- Separation of Duties (Least Privilege): Client uploaders are restricted
  from accessing moderator queues, blocklist entries, or audit logs.
- Constant-Time Comparison: Uses `hmac.compare_digest` to prevent timing attacks.
  Standard string comparisons (`==`) exit early on the first mismatched byte,
  allowing an attacker to infer secret characters by measuring microscopic
  latency differences.
- Safe Error Handling:
  - Missing key -> HTTP 401 Unauthorized (with WWW-Authenticate header hint).
  - Invalid key -> HTTP 403 Forbidden.
"""

import hmac
import logging
from typing import Optional
from fastapi import Header, HTTPException, status
from app.config import settings

logger = logging.getLogger(__name__)


def verify_client_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    FastAPI dependency that authenticates client upload requests.
    Validates against CLIENT_API_KEY in constant time.
    """
    if not x_api_key:
        logger.warning("Authentication failure: Missing X-API-Key on client endpoint.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing X-API-Key header.",
        )

    expected = settings.CLIENT_API_KEY.encode("utf-8")
    provided = x_api_key.encode("utf-8")

    # Constant-time comparison prevents timing side-channel attacks
    if not hmac.compare_digest(provided, expected):
        logger.warning("Authentication failure: Invalid client X-API-Key.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Invalid client API key.",
        )

    return x_api_key


def verify_admin_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    FastAPI dependency that authenticates moderator / administrative requests.
    Validates against ADMIN_API_KEY in constant time.
    """
    if not x_api_key:
        logger.warning("Authentication failure: Missing X-API-Key on admin endpoint.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing X-API-Key header for administrative access.",
        )

    expected = settings.ADMIN_API_KEY.encode("utf-8")
    provided = x_api_key.encode("utf-8")

    if not hmac.compare_digest(provided, expected):
        logger.warning("Authentication failure: Invalid admin X-API-Key.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Invalid administrator API key.",
        )

    return x_api_key


def verify_any_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    FastAPI dependency that accepts either CLIENT_API_KEY or ADMIN_API_KEY.
    Used for endpoints accessible to both clients and moderators (e.g. submitting appeals).
    """
    if not x_api_key:
        logger.warning("Authentication failure: Missing X-API-Key.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing X-API-Key header.",
        )

    provided = x_api_key.encode("utf-8")
    client_expected = settings.CLIENT_API_KEY.encode("utf-8")
    admin_expected = settings.ADMIN_API_KEY.encode("utf-8")

    is_client = hmac.compare_digest(provided, client_expected)
    is_admin = hmac.compare_digest(provided, admin_expected)

    if not (is_client or is_admin):
        logger.warning("Authentication failure: Invalid API key on shared endpoint.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Invalid API key.",
        )

    return x_api_key

