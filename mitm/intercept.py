"""
SafeGate — mitmproxy Interceptor Addon (Network-Level Fail-Closed Gateway)
==========================================================================
Demonstrates network-level enforcement in a controlled research / lab environment.
Intercepts outbound HTTP/HTTPS POST requests containing multipart video uploads,
extracts the media payload in real time, and queries SafeGate's `/api/upload` screening API.

ENFORCEMENT POLICY:
1. Verdict == "ALLOW": Request passes through transparently to the destination server.
2. Verdict == "BLOCK" or "REVIEW": Request is terminated at the proxy; client receives
   HTTP 403 Forbidden with "Blocked by SafeGate: policy violation".
3. Fail-Closed Resilience: If the SafeGate server is offline, times out, or throws an error,
   the proxy BLOCKS the upload with HTTP 403. An upload is NEVER allowed through unchecked.

IMPORTANT ETHICAL & LEGAL NOTICE:
TLS interception (MITM) decrypts network traffic and requires installing a custom root CA
certificate. This addon is strictly intended for isolated laboratory testbeds and educational
demonstration. In production architectures, upload screening is enforced either via:
- API Gateway / Reverse Proxy (e.g., Envoy, Kong, Cloudflare Workers).
- Platform upload pre-signed URL lambdas (e.g., AWS S3 Object Lambda, Cloudflare Stream Webhooks).

VIVA EXPLANATION:
- How does mitmproxy intercept HTTPS? The client machine trusts the proxy's generated Root CA.
  The proxy terminates the client's TLS handshake, inspects/modifies the payload, and re-encrypts
  it toward the destination server.
- Why fail-closed? In cybersecurity, an attacker can attempt Denial-of-Service against the screening
  gateway in hopes that the proxy will "fail-open" and pass uninspected payloads. By enforcing
  HTTP 403 on connection error, SafeGate guarantees zero bypass during gateway outages.
"""

import os
import re
import logging
from urllib.parse import urlparse
import urllib.request
import urllib.error
import json
from mitmproxy import http

# Configure logging
logger = logging.getLogger("safegate-mitm")
logging.basicConfig(level=logging.INFO)

# Configurable endpoints via environment variables
SAFEGATE_API_URL = os.environ.get("SAFEGATE_URL", "http://127.0.0.1:8000/api/upload")
SAFEGATE_CLIENT_KEY = os.environ.get("SAFEGATE_CLIENT_KEY", "dev-client-key-change-in-production-98765")
SAFEGATE_TIMEOUT_SEC = int(os.environ.get("SAFEGATE_TIMEOUT_SEC", "15"))

# Allowed / screened video extensions
VIDEO_EXT_REGEX = re.compile(r'\.(mp4|mov|avi|mkv|webm)', re.IGNORECASE)


class SafeGateInterceptor:
    """
    mitmproxy Event Hook Addon for screening video uploads in transit.
    """

    def request(self, flow: http.HTTPFlow) -> None:
        """
        Triggered when an HTTP request is received by the proxy before forwarding upstream.
        """
        # Only inspect HTTP POST requests with a payload
        if flow.request.method.upper() != "POST" or not flow.request.content:
            return

        content_type = flow.request.headers.get("Content-Type", "")

        # Target multipart/form-data or direct video streams
        is_multipart = "multipart/form-data" in content_type.lower()
        is_video_content = "video/" in content_type.lower()

        if not (is_multipart or is_video_content):
            return

        # Check if the request contains video media
        filename, video_bytes = self._extract_video_payload(flow.request)
        if not video_bytes:
            return

        logger.info(
            "[SafeGate MITM] Intercepted video upload '%s' (%d bytes) destined for %s",
            filename,
            len(video_bytes),
            flow.request.pretty_url,
        )

        # Screen through SafeGate Gateway
        verdict, explanation = self._screen_with_safegate(filename, video_bytes)

        if verdict == "ALLOW":
            logger.info("[SafeGate MITM] Verdict ALLOW for '%s' — permitting upstream transit.", filename)
            # Add an advisory response header for transparency
            flow.request.headers["X-SafeGate-Screened"] = "ALLOW"
            return

        # FAIL-CLOSED: Any verdict other than ALLOW (BLOCK, REVIEW, or gateway failure) is denied
        logger.warning(
            "[SafeGate MITM] Rejecting upload '%s': Verdict='%s', Reason='%s'",
            filename,
            verdict,
            explanation,
        )
        flow.response = http.Response.make(
            403,
            f"Blocked by SafeGate: policy violation [{verdict}]\nReason: {explanation}\n".encode("utf-8"),
            {
                "Content-Type": "text/plain; charset=utf-8",
                "X-SafeGate-Verdict": verdict,
                "Connection": "close",
            },
        )

    def _extract_video_payload(self, request: http.Request):
        """
        Extracts raw video bytes from multipart body or direct stream.
        Returns: (filename: str, payload_bytes: bytes) or (None, None)
        """
        raw_body = request.content
        content_type = request.headers.get("Content-Type", "")

        # 1. Direct video content-type upload
        if "video/" in content_type.lower():
            return "direct_upload.mp4", raw_body

        # 2. Multipart form parsing
        # Simple extraction searching for filename="something.ext"
        match = re.search(rb'filename="([^"]+\.(?:mp4|mov|avi|mkv|webm))"', raw_body, re.IGNORECASE)
        if match:
            filename = match.group(1).decode("utf-8", errors="ignore")
            # Extract section after multipart header boundary (\r\n\r\n)
            parts = raw_body.split(b"\r\n\r\n", 1)
            if len(parts) > 1:
                # Truncate at final multipart boundary
                payload = parts[1].rsplit(b"\r\n--", 1)[0]
                return filename, payload
            return filename, raw_body

        return None, None

    def _screen_with_safegate(self, filename: str, video_bytes: bytes):
        """
        Submits video payload to SafeGate /api/upload endpoint.
        Implements FAIL-CLOSED error handling: any network failure or timeout
        results in a rejected verdict.
        """
        boundary = "----SafeGateMitmBoundary123456789"
        c_type = f"multipart/form-data; boundary={boundary}"

        # Construct multipart body manually to avoid external dependency issues
        body_parts = [
            f"--{boundary}".encode("utf-8"),
            f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode("utf-8"),
            b"Content-Type: video/mp4",
            b"",
            video_bytes,
            f"--{boundary}--".encode("utf-8"),
            b"",
        ]
        payload = b"\r\n".join(body_parts)

        req = urllib.request.Request(
            SAFEGATE_API_URL,
            data=payload,
            headers={
                "Content-Type": c_type,
                "X-API-Key": SAFEGATE_CLIENT_KEY,
                "Content-Length": str(len(payload)),
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=SAFEGATE_TIMEOUT_SEC) as response:
                status_code = response.getcode()
                resp_bytes = response.read()
                data = json.loads(resp_bytes.decode("utf-8"))
                verdict = data.get("verdict", "REVIEW")
                explanation = data.get("explanation", "Evaluated by SafeGate")
                return verdict, explanation

        except urllib.error.HTTPError as http_err:
            try:
                err_data = json.loads(http_err.read().decode("utf-8"))
                msg = err_data.get("detail", str(http_err))
            except Exception:
                msg = str(http_err)
            logger.error("[SafeGate MITM] SafeGate returned HTTP %d: %s", http_err.code, msg)
            return "BLOCK", f"Gateway rejected request: {msg}"

        except urllib.error.URLError as url_err:
            logger.critical("[SafeGate MITM] FAIL-CLOSED: SafeGate gateway unreachable: %s", url_err)
            return "BLOCK", "Fail-closed enforcement: SafeGate gateway is unreachable."

        except Exception as exc:
            logger.critical("[SafeGate MITM] FAIL-CLOSED: Unexpected exception: %s", exc)
            return "BLOCK", f"Fail-closed enforcement: {str(exc)}"


# Register addon with mitmproxy
addons = [SafeGateInterceptor()]
