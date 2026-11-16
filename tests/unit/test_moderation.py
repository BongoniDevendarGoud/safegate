from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from safegate_api.database import Base, get_db_session
from safegate_api.main import app
from safegate_api.models import FrameAnalysis, MediaUpload
from safegate_api.routes import storage_client


@pytest_asyncio.fixture
async def moderation_client(
    tmp_path: Path,
) -> AsyncGenerator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession]], None]:
    """Configures FastAPI test client with in-memory SQLite and local storage."""
    db_file = tmp_path / "test_mod.db"
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

    storage_client.local_storage_dir = tmp_path / "storage"
    (tmp_path / "storage" / "quarantine").mkdir(parents=True, exist_ok=True)
    (tmp_path / "storage" / "published").mkdir(parents=True, exist_ok=True)
    (tmp_path / "storage" / "vault").mkdir(parents=True, exist_ok=True)

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, session_maker

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_moderation_queue_and_actions(
    moderation_client: tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession]],
) -> None:
    """Verify listing moderation queue, viewing review package, and submitting APPROVE."""
    client, session_maker = moderation_client

    upload_id = "mod-test-001"
    q_key = f"default-tenant/{upload_id}/video.mp4"
    storage_client.upload_quarantine(key=q_key, data=b"fake-quarantine-content")

    # Seed an item in HUMAN_REVIEW status
    async with session_maker() as s:
        up = MediaUpload(
            id=upload_id,
            tenant_id="default-tenant",
            filename="video.mp4",
            file_size_bytes=1024,
            mime_type="video/mp4",
            sha256_hash="abc123mod",
            is_video=True,
            status="COMPLETED",
            verdict="HUMAN_REVIEW",
            quarantine_key=q_key,
            total_frames=2,
            yellow_frame_count=1,
            green_frame_count=1,
        )
        s.add(up)
        f1 = FrameAnalysis(
            upload_id=upload_id,
            frame_index=0,
            timestamp_ms=0,
            color="GREEN",
            deepfake_score=0.1,
            sensitive_score=0.05,
            uncertainty_score=0.1,
        )
        f2 = FrameAnalysis(
            upload_id=upload_id,
            frame_index=1,
            timestamp_ms=33,
            color="YELLOW",
            deepfake_score=0.2,
            sensitive_score=0.75,
            uncertainty_score=0.15,
        )
        s.add_all([f1, f2])
        await s.commit()

    # 1. Test GET /v1/moderation/queue
    resp_q = await client.get("/v1/moderation/queue")
    assert resp_q.status_code == 200
    q_data = resp_q.json()
    assert q_data["total_count"] == 1
    assert q_data["items"][0]["upload_id"] == upload_id
    assert q_data["items"][0]["yellow_frame_count"] == 1

    # 2. Test GET /v1/moderation/{upload_id}
    resp_pkg = await client.get(f"/v1/moderation/{upload_id}")
    assert resp_pkg.status_code == 200
    pkg_data = resp_pkg.json()
    assert pkg_data["blur_default"] is True  # Wellness protection
    assert len(pkg_data["frames"]) == 2

    # 3. Test POST /v1/moderation/{upload_id}/action -> APPROVE
    action_body = {
        "action": "APPROVE",
        "reviewer_id": "rev_lead_42",
        "notes": "Reviewed and cleared: cinematic special effects, acceptable for publication.",
        "category": "False Positive",
    }
    resp_act = await client.post(f"/v1/moderation/{upload_id}/action", json=action_body)
    assert resp_act.status_code == 200
    act_data = resp_act.json()
    assert act_data["final_verdict"] == "ALLOW"
    assert act_data["reviewer_id"] == "rev_lead_42"
    assert act_data["audit_sequence"] > 0

    # 4. Verify queue is now empty
    resp_q2 = await client.get("/v1/moderation/queue")
    assert resp_q2.json()["total_count"] == 0
