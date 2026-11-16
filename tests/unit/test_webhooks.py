import json
import time

import pytest

from safegate_api.webhooks import (
    WebhookDispatcher,
    sign_webhook_payload,
    verify_webhook_signature,
)


def test_webhook_sign_and_verify() -> None:
    """Verify HMAC signature generation and valid verification."""
    secret = "tenant_test_webhook_secret_32b_min"
    payload = json.dumps({"event": "verdict.ready", "upload_id": "test-123"}).encode()
    now_ts = int(time.time())

    signature = sign_webhook_payload(payload, secret, now_ts)
    assert len(signature) == 64

    is_valid = verify_webhook_signature(payload, signature, now_ts, secret)
    assert is_valid is True


def test_webhook_rejects_tampered_payload() -> None:
    """Verify tampering with payload fails verification."""
    secret = "tenant_test_webhook_secret_32b_min"
    payload = b'{"verdict":"ALLOW"}'
    now_ts = int(time.time())

    signature = sign_webhook_payload(payload, secret, now_ts)

    # Tampered payload
    tampered_payload = b'{"verdict":"BLOCK"}'
    assert not verify_webhook_signature(tampered_payload, signature, now_ts, secret)


def test_webhook_rejects_stale_timestamp() -> None:
    """Verify replay prevention rejects timestamps older than drift limit."""
    secret = "tenant_test_webhook_secret_32b_min"
    payload = b'{"verdict":"ALLOW"}'
    old_ts = int(time.time()) - 400  # 400 seconds in past (> 300s limit)

    signature = sign_webhook_payload(payload, secret, old_ts)
    assert not verify_webhook_signature(payload, signature, old_ts, secret, max_drift_seconds=300)


@pytest.mark.asyncio
async def test_webhook_dispatcher_retry_failure() -> None:
    """Verify dispatcher returns delivery failure when target URL is unreachable."""
    dispatcher = WebhookDispatcher(default_timeout_sec=0.2)
    res = await dispatcher.dispatch_verdict_webhook(
        target_url="http://127.0.0.1:59999/nonexistent",
        secret="test-sec",
        event_type="safegate.verdict.ready",
        upload_id="up-1",
        tenant_id="tenant-1",
        verdict="ALLOW",
        data={"score": 0.1},
        max_retries=1,
    )

    assert res.success is False
    assert res.status_code == 0
    assert res.error_message is not None
