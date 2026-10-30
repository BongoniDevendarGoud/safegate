"""
SafeGate — CORS Configuration Module
======================================
Configures Cross-Origin Resource Sharing (CORS).

SECURITY RULE:
- SafeGate strictly permits requests originating from the configured `DASHBOARD_ORIGIN`
  (default: http://localhost:8000).
- Prohibits wildcard (`*`) access to prevent unauthorized cross-origin requests
  from arbitrary third-party websites (Cross-Site Request Forgery / CSRF defense).
"""

from fastapi.middleware.cors import CORSMiddleware
from app.config import settings


def configure_cors(app) -> None:
    """
    Registers strict CORSMiddleware on the FastAPI application instance.
    """
    allowed_origins = [settings.DASHBOARD_ORIGIN]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["X-API-Key", "Content-Type", "Authorization"],
    )
