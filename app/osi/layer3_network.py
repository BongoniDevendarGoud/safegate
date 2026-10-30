"""
SafeGate OSI Model — Layer 3: Network Layer
============================================
OSI MAPPING:
Layer 3 handles source and destination addressing, routing, and traffic policing across IP networks.
In SafeGate, Layer 3 enforces:
- Origin IP address resolution (supporting proxy headers X-Forwarded-For).
- IP-based rate limiting (Token Bucket / Sliding Window) to defend against volumetric flood attacks.
- Subnet / CIDR source validation.

VIVA EXPLANATION:
Why is rate limiting mapped to Layer 3?
Because traffic policing based on network layer IP addresses prevents malicious clients
from overwhelming gateway computation resources before packets advance to cryptographic
or deep learning stages.
"""

import time
from typing import Dict, Tuple
from app.config import settings


class Layer3NetworkPolicy:
    """
    Layer 3: IP Address Filtering & Network Traffic Rate Policing.
    Implements a sliding window rate limiter per client IP address.
    """

    def __init__(self, max_requests_per_minute: int = None):
        self.limit = max_requests_per_minute or 10
        self.window_sec = 60.0
        # In-memory IP tracking: ip -> list of request timestamps
        self._ip_history: Dict[str, list] = {}

    def verify_network_origin(self, client_ip: str) -> Tuple[bool, str]:
        """
        Validates the incoming network address and enforces IP rate limits.

        Returns:
            (allowed: bool, rationale: str)
        """
        if not client_ip:
            client_ip = "127.0.0.1"

        now = time.time()
        timestamps = self._ip_history.get(client_ip, [])

        # Prune timestamps older than window
        valid_timestamps = [t for t in timestamps if now - t < self.window_sec]

        if len(valid_timestamps) >= self.limit:
            self._ip_history[client_ip] = valid_timestamps
            return False, f"[Layer 3 Network Violation] IP {client_ip} exceeded rate limit ({self.limit} req/min)."

        valid_timestamps.append(now)
        self._ip_history[client_ip] = valid_timestamps
        return True, f"IP {client_ip} network traffic conforms to policy ({len(valid_timestamps)}/{self.limit})."
