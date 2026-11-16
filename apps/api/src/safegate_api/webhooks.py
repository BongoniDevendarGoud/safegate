"""
SafeGate Signed Webhook Dispatcher Subsystem.
Signs outgoing HTTP callbacks using HMAC-SHA256 and manages retry delivery.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from safegate_api.logging import logger


@dataclass(frozen=True)
class WebhookDeliveryResult:
    success: bool
    status_code: int
    attempt_count: int
    delivered_at: str
    error_message: str | None = None


def sign_webhook_payload(payload_bytes: bytes, secret: str, timestamp_sec: int) -> str:
    """
    Computes HMAC-SHA256 signature over timestamp and payload bytes.
    Signature format: HMAC_SHA256(secret, f"{timestamp}.{payload}")
    """
    to_sign = f"{timestamp_sec}.".encode() + payload_bytes
    return hmac.new(key=secret.encode("utf-8"), msg=to_sign, digestmod=hashlib.sha256).hexdigest()


def verify_webhook_signature(
    payload_bytes: bytes,
    signature: str,
    timestamp_sec: int,
    secret: str,
    max_drift_seconds: int = 300,
) -> bool:
    """
    Verifies incoming webhook signature and checks timestamp to prevent replay attacks.
    """
    now = int(time.time())
    if abs(now - timestamp_sec) > max_drift_seconds:
        logger.warning(
            f"Webhook rejected: timestamp drift ({abs(now - timestamp_sec)}s) exceeds limit ({max_drift_seconds}s)"
        )
        return False

    expected_sig = sign_webhook_payload(payload_bytes, secret, timestamp_sec)
    return hmac.compare_digest(expected_sig, signature)


class WebhookDispatcher:
    """
    Dispatches cryptographically signed webhook notifications to host platform endpoints.
    """

    def __init__(self, default_timeout_sec: float = 5.0) -> None:
        self.default_timeout = default_timeout_sec

    async def dispatch_verdict_webhook(
        self,
        target_url: str,
        secret: str,
        event_type: str,
        upload_id: str,
        tenant_id: str,
        verdict: str,
        data: dict[str, Any],
        max_retries: int = 3,
    ) -> WebhookDeliveryResult:
        """
        Sends signed JSON webhook with exponential backoff on transient errors.
        """
        now = datetime.now(UTC)
        ts_sec = int(now.timestamp())

        payload_obj = {
            "event": event_type,
            "upload_id": upload_id,
            "tenant_id": tenant_id,
            "verdict": verdict,
            "timestamp": now.isoformat(),
            "data": data,
        }
        canonical_bytes = json.dumps(payload_obj, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        signature = sign_webhook_payload(canonical_bytes, secret, ts_sec)

        headers = {
            "Content-Type": "application/json",
            "X-SafeGate-Signature": signature,
            "X-SafeGate-Timestamp": str(ts_sec),
            "X-SafeGate-Event": event_type,
        }

        async with httpx.AsyncClient(timeout=self.default_timeout) as client:
            last_err = None
            for attempt in range(1, max_retries + 1):
                try:
                    resp = await client.post(target_url, content=canonical_bytes, headers=headers)
                    if 200 <= resp.status_code < 300:
                        logger.info(
                            f"Webhook {event_type} delivered to {target_url} for upload {upload_id} (attempt {attempt})"
                        )
                        return WebhookDeliveryResult(
                            success=True,
                            status_code=resp.status_code,
                            attempt_count=attempt,
                            delivered_at=datetime.now(UTC).isoformat(),
                        )
                    else:
                        last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                except Exception as exc:
                    last_err = str(exc)

                # Exponential backoff: 0.1s, 0.2s, 0.4s in test/dev
                await asyncio.sleep(0.05 * (2**attempt))

        logger.error(
            f"Webhook delivery failed after {max_retries} attempts to {target_url}: {last_err}"
        )
        return WebhookDeliveryResult(
            success=False,
            status_code=0,
            attempt_count=max_retries,
            delivered_at=datetime.now(UTC).isoformat(),
            error_message=last_err,
        )
