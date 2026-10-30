"""
SafeGate — IP Rate Limiting Module
====================================
Prevents Denial-of-Service (DoS) and brute-force upload flooding using
the `slowapi` rate limiting framework.

HOW IT WORKS:
- Tracks requests by client remote IP address (`get_remote_address`).
- Rate threshold is configured via RATE_LIMIT_PER_MINUTE (default: 10/min).
- On limit exhaustion, returns HTTP 429 Too Many Requests with a `Retry-After` header.
"""

import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
from app.config import settings

logger = logging.getLogger(__name__)

# Singleton rate limiter instance keyed by client IP address
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Standardized response returned when an IP exceeds its upload quota.
    Suppresses internal details and sets HTTP 429 status.
    """
    client_ip = get_remote_address(request)
    logger.warning("Rate limit exceeded for IP %s on %s %s", client_ip, request.method, request.url.path)

    response = JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded: Maximum {settings.RATE_LIMIT_PER_MINUTE} uploads per minute allowed. Please wait before retrying."
        },
    )
    response.headers["Retry-After"] = "60"
    return response
