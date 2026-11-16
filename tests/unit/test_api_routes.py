from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from safegate_api.database import Base, get_db_session
from safegate_api.main import app
from safegate_api.routes import storage_client


@pytest_asyncio.fixture
async def test_app_client(tmp_path: Path) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Configures FastAPI test client with in-memory SQLite and local storage."""
    db_file = tmp_path / "test_api.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # Override storage directory
    storage_client.local_storage_dir = tmp_path
    (tmp_path / "quarantine").mkdir(parents=True, exist_ok=True)
    (tmp_path / "published").mkdir(parents=True, exist_ok=True)
    (tmp_path / "vault").mkdir(parents=True, exist_ok=True)

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_healthcheck_endpoint(test_app_client: httpx.AsyncClient) -> None:
    """Verify /v1/healthz returns 200 OK and database status."""
    resp = await test_app_client.get("/v1/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["fail_closed_mode"] is True
    assert data["database_connected"] is True


@pytest.mark.asyncio
async def test_upload_media_valid_mp4(test_app_client: httpx.AsyncClient) -> None:
    """Verify media intake accepts valid MP4 bytes and places file in quarantine."""
    # Synthesize valid MP4 header
    mp4_bytes = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2mp41" + (b"\x00" * 100)

    files = {"file": ("sample_test.mp4", mp4_bytes, "video/mp4")}
    headers = {"X-Tenant-ID": "tenant-test-xyz"}

    resp = await test_app_client.post("/v1/media/upload", files=files, headers=headers)
    assert resp.status_code == 202
    data = resp.json()

    assert data["status"] == "QUEUED"
    assert data["verdict"] == "PENDING"
    assert data["mime_type"] == "video/mp4"
    assert data["tenant_id"] == "tenant-test-xyz"
    assert "upload_id" in data
    assert len(data["sha256_hash"]) == 64

    # Verify query status endpoint
    upload_id = data["upload_id"]
    status_resp = await test_app_client.get(f"/v1/media/{upload_id}", headers=headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["upload_id"] == upload_id
    assert status_data["status"] == "QUEUED"


@pytest.mark.asyncio
async def test_upload_media_rejects_corrupted_header(test_app_client: httpx.AsyncClient) -> None:
    """Verify media intake returns RFC 7807 415 error for unsupported format."""
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00" + (b"\x00" * 20)

    files = {"file": ("malicious.exe", fake_exe, "application/octet-stream")}
    resp = await test_app_client.post("/v1/media/upload", files=files)
    assert resp.status_code == 415

    data = resp.json()
    assert data["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert data["status"] == 415


@pytest.mark.asyncio
async def test_audit_verify_endpoint(test_app_client: httpx.AsyncClient) -> None:
    """Verify /v1/audit/verify endpoint checks ledger integrity."""
    resp = await test_app_client.get("/v1/audit/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
