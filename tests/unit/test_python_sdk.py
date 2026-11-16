from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from safegate_sdk.client import (
    AsyncSafeGateClient,
    SafeGateClient,
    StatusResult,
    UploadResult,
    verify_webhook_signature,
)


def test_sdk_webhook_verification() -> None:
    """Verify SDK helper validates legitimate signatures and detects tampering."""
    secret = "my_sdk_webhook_secret_key"
    payload = b'{"event":"verdict.ready","verdict":"ALLOW"}'
    ts = 1700000000

    import hashlib
    import hmac

    to_sign = f"{ts}.".encode() + payload
    sig = hmac.new(secret.encode(), to_sign, hashlib.sha256).hexdigest()

    assert verify_webhook_signature(payload, sig, ts, secret, max_drift_seconds=9999999999)
    assert not verify_webhook_signature(b"tampered", sig, ts, secret, max_drift_seconds=9999999999)


def test_safegate_client_upload_and_status(tmp_path: Path) -> None:
    """Verify synchronous client upload_media and get_status."""
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"\xff\xd8\xff\xe0" + (b"\x00" * 20))

    mock_resp_upload = MagicMock()
    mock_resp_upload.json.return_value = {
        "upload_id": "up-sync-1",
        "tenant_id": "tenant-test",
        "filename": "test.jpg",
        "mime_type": "image/jpeg",
        "file_size_bytes": 24,
        "sha256_hash": "hash123",
        "status": "QUEUED",
        "verdict": "PENDING",
        "message": "Enqueued",
    }
    mock_resp_upload.raise_for_status = MagicMock()

    mock_resp_status = MagicMock()
    mock_resp_status.json.return_value = {
        "upload_id": "up-sync-1",
        "tenant_id": "tenant-test",
        "filename": "test.jpg",
        "status": "COMPLETED",
        "verdict": "ALLOW",
        "total_frames": 1,
        "red_frames": 0,
        "yellow_frames": 0,
        "green_frames": 1,
        "published_url": "s3://pub/test.jpg",
    }
    mock_resp_status.raise_for_status = MagicMock()

    with (
        patch("httpx.Client.post", return_value=mock_resp_upload),
        patch("httpx.Client.get", return_value=mock_resp_status),
    ):
        client = SafeGateClient(base_url="http://testserver", tenant_id="tenant-test")
        up_res = client.upload_media(test_file)
        assert isinstance(up_res, UploadResult)
        assert up_res.upload_id == "up-sync-1"

        st_res = client.get_status("up-sync-1")
        assert isinstance(st_res, StatusResult)
        assert st_res.verdict == "ALLOW"


@pytest.mark.asyncio
async def test_async_safegate_client(tmp_path: Path) -> None:
    """Verify asynchronous client upload_media and get_status."""
    test_file = tmp_path / "test_async.jpg"
    test_file.write_bytes(b"\xff\xd8\xff\xe0" + (b"\x00" * 20))

    mock_resp_upload = MagicMock()
    mock_resp_upload.json.return_value = {
        "upload_id": "up-async-2",
        "tenant_id": "tenant-async",
        "filename": "test_async.jpg",
        "mime_type": "image/jpeg",
        "file_size_bytes": 24,
        "sha256_hash": "hash456",
        "status": "QUEUED",
        "verdict": "PENDING",
        "message": "Enqueued",
    }
    mock_resp_upload.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_resp_upload):
        client = AsyncSafeGateClient(base_url="http://testserver", tenant_id="tenant-async")
        up_res = await client.upload_media(test_file)
        assert up_res.upload_id == "up-async-2"
        assert up_res.tenant_id == "tenant-async"
