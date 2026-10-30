"""
SafeGate — Security Headers Middleware
========================================
Injects defensive HTTP response headers to harden the application against
common web vulnerabilities:

1. `X-Content-Type-Options: nosniff`
   Prevents MIME-sniffing: instructs browsers not to override the declared
   Content-Type, preventing script execution from uploaded files.
2. `X-Frame-Options: DENY`
   Mitigates Clickjacking attacks by prohibiting embedding in `<iframe>` tags.
3. `Strict-Transport-Security: max-age=31536000; includeSubDomains`
   Enforces encrypted HTTPS connections (HSTS).
4. `Content-Security-Policy` (CSP):
   Restricts the origin of executable scripts, stylesheets, and assets.
5. `Referrer-Policy: strict-origin-when-cross-origin`
   Limits leakage of internal query parameters and path information in HTTP Referer.
6. `Permissions-Policy`
   Disables browser hardware APIs (camera, microphone, geolocation).
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from fastapi import Request, Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies security headers to every outgoing HTTP response.
    """
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # 1. Prevent MIME-type confusion attacks
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 2. Defend against UI redressing / clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # 3. HTTP Strict Transport Security
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # 4. Content Security Policy (allows self and cdn for Chart.js)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )

        # 5. Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 6. Restrict unnecessary browser capabilities
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        return response
