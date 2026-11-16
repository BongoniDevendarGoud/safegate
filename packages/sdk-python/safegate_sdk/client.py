"""
SafeGate Client SDK implementation.
Provides synchronous and asynchronous clients for host platform media screening.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


@dataclass(frozen=True)
class UploadResult:
    upload_id: str
    tenant_id: str
    filename: str
    mime_type: str
    file_size_bytes: int
    sha256_hash: str
    status: str
    verdict: str
    message: str


@dataclass(frozen=True)
class StatusResult:
    upload_id: str
    tenant_id: str
    filename: str
    status: str
    verdict: str
    total_frames: int
    red_frames: int
    yellow_frames: int
    green_frames: int
    published_url: str | None
    raw_data: dict[str, Any]


def verify_webhook_signature(
    payload_bytes: bytes,
    signature: str,
    timestamp_sec: int,
    secret: str,
    max_drift_seconds: int = 300,
) -> bool:
    """Verifies HMAC-SHA256 signature on incoming webhooks from SafeGate."""
    now = int(time.time())
    if abs(now - timestamp_sec) > max_drift_seconds:
        return False
    to_sign = f"{timestamp_sec}.".encode() + payload_bytes
    expected = hmac.new(
        key=secret.encode("utf-8"), msg=to_sign, digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


class SafeGateClient:
    """Synchronous SafeGate SDK client."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        tenant_id: str = "default-tenant",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.tenant_id = tenant_id
        self.timeout = timeout

    def upload_media(self, file_path: str | Path) -> UploadResult:
        """Uploads a local media file to SafeGate for firewall screening."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        headers = {"X-Tenant-ID": self.tenant_id}
        with open(path, "rb") as f:
            files = {"file": (path.name, f, "application/octet-stream")}
            with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
                resp = client.post("/v1/media/upload", files=files, headers=headers)
                resp.raise_for_status()
                d = resp.json()
                return UploadResult(
                    upload_id=d["upload_id"],
                    tenant_id=d["tenant_id"],
                    filename=d["filename"],
                    mime_type=d["mime_type"],
                    file_size_bytes=d["file_size_bytes"],
                    sha256_hash=d["sha256_hash"],
                    status=d["status"],
                    verdict=d["verdict"],
                    message=d["message"],
                )

    def get_status(self, upload_id: str) -> StatusResult:
        """Queries the current status and verdict of an upload."""
        headers = {"X-Tenant-ID": self.tenant_id}
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            resp = client.get(f"/v1/media/{upload_id}", headers=headers)
            resp.raise_for_status()
            d = resp.json()
            return StatusResult(
                upload_id=d["upload_id"],
                tenant_id=d["tenant_id"],
                filename=d["filename"],
                status=d["status"],
                verdict=d["verdict"],
                total_frames=d["total_frames"],
                red_frames=d["red_frames"],
                yellow_frames=d["yellow_frames"],
                green_frames=d["green_frames"],
                published_url=d.get("published_url"),
                raw_data=d,
            )

    def wait_for_verdict(
        self,
        upload_id: str,
        poll_interval_sec: float = 0.5,
        timeout_sec: float = 30.0,
    ) -> StatusResult:
        """Polls until status is COMPLETED or FAILED, or timeout elapses."""
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            res = self.get_status(upload_id)
            if res.status in {"COMPLETED", "FAILED"}:
                return res
            time.sleep(poll_interval_sec)
        raise TimeoutError(f"Upload '{upload_id}' did not complete within {timeout_sec}s")


class AsyncSafeGateClient:
    """Asynchronous SafeGate SDK client."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        tenant_id: str = "default-tenant",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.tenant_id = tenant_id
        self.timeout = timeout

    async def upload_media(self, file_path: str | Path) -> UploadResult:
        """Uploads a local media file asynchronously to SafeGate."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        headers = {"X-Tenant-ID": self.tenant_id}
        file_bytes = path.read_bytes()
        files = {"file": (path.name, file_bytes, "application/octet-stream")}

        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post("/v1/media/upload", files=files, headers=headers)
            resp.raise_for_status()
            d = resp.json()
            return UploadResult(
                upload_id=d["upload_id"],
                tenant_id=d["tenant_id"],
                filename=d["filename"],
                mime_type=d["mime_type"],
                file_size_bytes=d["file_size_bytes"],
                sha256_hash=d["sha256_hash"],
                status=d["status"],
                verdict=d["verdict"],
                message=d["message"],
            )

    async def get_status(self, upload_id: str) -> StatusResult:
        """Queries status asynchronously."""
        headers = {"X-Tenant-ID": self.tenant_id}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.get(f"/v1/media/{upload_id}", headers=headers)
            resp.raise_for_status()
            d = resp.json()
            return StatusResult(
                upload_id=d["upload_id"],
                tenant_id=d["tenant_id"],
                filename=d["filename"],
                status=d["status"],
                verdict=d["verdict"],
                total_frames=d["total_frames"],
                red_frames=d["red_frames"],
                yellow_frames=d["yellow_frames"],
                green_frames=d["green_frames"],
                published_url=d.get("published_url"),
                raw_data=d,
            )

    async def wait_for_verdict(
        self,
        upload_id: str,
        poll_interval_sec: float = 0.5,
        timeout_sec: float = 30.0,
    ) -> StatusResult:
        """Asynchronously polls until processing finishes."""
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            res = await self.get_status(upload_id)
            if res.status in {"COMPLETED", "FAILED"}:
                return res
            await asyncio.sleep(poll_interval_sec)
        raise TimeoutError(f"Upload '{upload_id}' did not complete within {timeout_sec}s")
