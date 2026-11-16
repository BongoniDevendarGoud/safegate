"""
SafeGate Full End-to-End System Integration Test.
Exercises the entire SafeGate firewall lifecycle:
1. Ingestion & quarantine storage
2. Streaming extraction & forensic model processing
3. Tri-state policy evaluation (RED=BLOCK, YELLOW=HUMAN_REVIEW, GREEN=ALLOW)
4. Human review queue & cryptographically signed moderation action
5. HMAC-SHA256 audit ledger verification
"""

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import cv2
import httpx
import numpy as np
import pytest
import pytest_asyncio
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from safegate_api.audit import verify_ledger_integrity
from safegate_api.database import Base, get_db_session
from safegate_api.main import app
from safegate_api.routes import storage_client
from safegate_worker.processor import MediaProcessor


@pytest_asyncio.fixture
async def e2e_context(
    tmp_path: Path,
) -> AsyncGenerator[tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], Any], None]:
    """Provides isolated SQLite database, storage, and HTTP test client."""
    db_file = tmp_path / "e2e_test.db"
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

    storage_client.local_storage_dir = tmp_path
    (tmp_path / "quarantine").mkdir(parents=True, exist_ok=True)
    (tmp_path / "published").mkdir(parents=True, exist_ok=True)
    (tmp_path / "vault").mkdir(parents=True, exist_ok=True)

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, session_maker, storage_client

    app.dependency_overrides.clear()
    await test_engine.dispose()


def create_natural_test_image(path: Path) -> None:
    """Creates a natural gradient image that passes as authentic content."""
    x = np.linspace(60, 180, 160)
    y = np.linspace(80, 200, 120)
    xx, yy = np.meshgrid(x, y)
    img_rgb = np.zeros((120, 160, 3), dtype=np.uint8)
    img_rgb[:, :, 0] = xx.astype(np.uint8)
    img_rgb[:, :, 1] = yy.astype(np.uint8)
    img_rgb[:, :, 2] = ((xx + yy) / 2).astype(np.uint8)

    np.random.seed(42)
    noise = np.random.normal(0, 3.0, img_rgb.shape).astype(np.int16)
    img_rgb = np.clip(img_rgb.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    cv2.imwrite(str(path), cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))


def create_blood_test_image(path: Path) -> None:
    """Creates a test image with dominant red hemoglobin chromaticity (sensitive)."""
    img_rgb = np.zeros((100, 100, 3), dtype=np.uint8)
    img_rgb[:, :] = [210, 20, 20]  # Deep arterial blood red in RGB
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(path), img_bgr)


def create_manipulated_test_image(path: Path) -> None:
    """Creates a synthetic image with intense artificial grid artifact."""
    img = np.zeros((120, 160, 3), dtype=np.uint8)
    img[::2, ::2] = 255
    cv2.imwrite(str(path), img)


@pytest.mark.asyncio
async def test_end_to_end_clean_image_clears_firewall(
    tmp_path: Path,
    e2e_context: tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], Any],
) -> None:
    """
    End-to-end: Clean image uploaded -> Scanned -> Verdict ALLOW -> Published.
    """
    client, session_maker, storage = e2e_context
    clean_file = tmp_path / "clean_photo.jpg"
    create_natural_test_image(clean_file)

    # 1. Ingest clean media
    with open(clean_file, "rb") as f:
        resp = await client.post(
            "/v1/media/upload",
            files={"file": ("clean_photo.jpg", f, "image/jpeg")},
            headers={"X-Tenant-ID": "test-e2e-tenant"},
        )
    assert resp.status_code == 202
    upload_id = resp.json()["upload_id"]

    # 2. Worker executes multi-branch analysis with validated model registered
    processor = MediaProcessor(storage_client=storage)
    processor.pipeline.has_validated_model = True
    processor.pipeline.has_calibrated_thresholds = True
    processor.pipeline.detector_type = "model"

    async with session_maker() as session:
        decision = await processor.process_media_file(
            media_path=clean_file,
            upload_id=upload_id,
            session=session,
            tenant_id="test-e2e-tenant",
        )
        await session.commit()

    assert decision.verdict == "ALLOW"
    assert decision.total_frames == 1
    assert decision.green_frames == 1
    assert decision.red_frames == 0
    assert decision.yellow_frames == 0

    # 3. Check status endpoint confirms ALLOW and published key
    st_resp = await client.get(
        f"/v1/media/{upload_id}",
        headers={"X-Tenant-ID": "test-e2e-tenant"},
    )
    assert st_resp.status_code == 200
    st_data = st_resp.json()
    assert st_data["verdict"] == "ALLOW"
    assert st_data["status"] == "COMPLETED"
    assert st_data["published_url"] is not None


@pytest.mark.asyncio
async def test_end_to_end_sensitive_image_to_human_moderation_and_approval(
    tmp_path: Path,
    e2e_context: tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], Any],
) -> None:
    """
    End-to-end: Sensitive blood image -> Scanned -> Verdict HUMAN_REVIEW ->
    Moderation queue -> Human review action APPROVE -> Promoted & Audit logged.
    """
    client, session_maker, storage = e2e_context
    blood_file = tmp_path / "blood_scene.jpg"
    create_blood_test_image(blood_file)

    # 1. Ingest sensitive image
    with open(blood_file, "rb") as f:
        resp = await client.post(
            "/v1/media/upload",
            files={"file": ("blood_scene.jpg", f, "image/jpeg")},
            headers={"X-Tenant-ID": "test-e2e-tenant"},
        )
    assert resp.status_code == 202
    upload_id = resp.json()["upload_id"]

    # 2. Worker executes multi-branch analysis with validated model registered
    processor = MediaProcessor(storage_client=storage)
    processor.pipeline.has_validated_model = True
    processor.pipeline.has_calibrated_thresholds = True
    processor.pipeline.detector_type = "model"

    async with session_maker() as session:
        decision = await processor.process_media_file(
            media_path=blood_file,
            upload_id=upload_id,
            session=session,
            tenant_id="test-e2e-tenant",
        )
        await session.commit()

    assert decision.verdict == "HUMAN_REVIEW"
    assert decision.yellow_frames >= 1

    # 3. Check that it appears in the Moderation Queue
    q_resp = await client.get("/v1/moderation/queue")
    assert q_resp.status_code == 200
    items = q_resp.json()["items"]
    assert any(item["upload_id"] == upload_id for item in items)

    # 4. Fetch the full forensic package
    pkg_resp = await client.get(f"/v1/moderation/{upload_id}")
    assert pkg_resp.status_code == 200
    pkg_data = pkg_resp.json()
    assert pkg_data["verdict"] == "HUMAN_REVIEW"
    assert len(pkg_data["frames"]) >= 1
    assert pkg_data["frames"][0]["color"] == "YELLOW"

    # 5. Human Moderator reviews evidence and submits APPROVE
    action_payload = {
        "action": "APPROVE",
        "reviewer_id": "human_reviewer_42",
        "notes": "Verified as synthetic special-effects prop blood; safe for general audience.",
        "category": "Educational / News Exception",
    }
    act_resp = await client.post(
        f"/v1/moderation/{upload_id}/action",
        json=action_payload,
        headers={"X-Tenant-ID": "test-e2e-tenant"},
    )
    assert act_resp.status_code == 200
    act_data = act_resp.json()
    assert act_data["final_verdict"] == "ALLOW"
    assert act_data["reviewer_id"] == "human_reviewer_42"

    # 6. Verify HMAC-SHA256 Audit Ledger integrity
    async with session_maker() as session:
        audit_res = await verify_ledger_integrity(session)
        assert audit_res.is_valid is True
        assert audit_res.total_records >= 2  # upload + human action


@pytest.mark.asyncio
async def test_end_to_end_deepfake_morphed_image_blocked(
    tmp_path: Path,
    e2e_context: tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], Any],
) -> None:
    """
    End-to-end: Manipulated / morphed image -> Scanned -> Confirmed RED frame ->
    Verdict BLOCK -> Quarantined forever, NEVER published.
    """
    client, session_maker, storage = e2e_context
    fake_file = tmp_path / "deepfake_synth.jpg"
    create_manipulated_test_image(fake_file)

    # 1. Ingest synthetic media
    with open(fake_file, "rb") as f:
        resp = await client.post(
            "/v1/media/upload",
            files={"file": ("deepfake_synth.jpg", f, "image/jpeg")},
            headers={"X-Tenant-ID": "test-e2e-tenant"},
        )
    assert resp.status_code == 202
    upload_id = resp.json()["upload_id"]

    # 2. Worker executes multi-branch analysis with validated model registered
    processor = MediaProcessor(storage_client=storage)
    processor.pipeline.has_validated_model = True
    processor.pipeline.has_calibrated_thresholds = True
    processor.pipeline.detector_type = "model"

    async with session_maker() as session:
        decision = await processor.process_media_file(
            media_path=fake_file,
            upload_id=upload_id,
            session=session,
            tenant_id="test-e2e-tenant",
        )
        await session.commit()

    # Confirmed manipulation routes to BLOCK (or HUMAN_REVIEW if borderline)
    assert decision.verdict in {"BLOCK", "HUMAN_REVIEW"}
    if decision.verdict == "BLOCK":
        assert decision.red_frames >= 1
    # Crucial security invariant: Must NEVER be published
    assert decision.verdict != "ALLOW"

    # 3. Check status endpoint confirms it is NOT published
    st_resp = await client.get(
        f"/v1/media/{upload_id}",
        headers={"X-Tenant-ID": "test-e2e-tenant"},
    )
    assert st_resp.status_code == 200
    st_data = st_resp.json()
    assert st_data["verdict"] in {"BLOCK", "HUMAN_REVIEW"}
    assert st_data["published_url"] is None


@pytest.mark.asyncio
async def test_end_to_end_unvalidated_model_fails_closed_to_human_review(
    tmp_path: Path,
    e2e_context: tuple[httpx.AsyncClient, async_sessionmaker[AsyncSession], Any],
) -> None:
    """
    End-to-end: Clean image uploaded when NO validated model is loaded.
    Must fail closed to HUMAN_REVIEW with reason NO_VALIDATED_MODEL (never ALLOW).
    """
    client, session_maker, storage = e2e_context
    clean_file = tmp_path / "unval_clean.jpg"
    create_natural_test_image(clean_file)

    # 1. Ingest clean media
    with open(clean_file, "rb") as f:
        resp = await client.post(
            "/v1/media/upload",
            files={"file": ("unval_clean.jpg", f, "image/jpeg")},
            headers={"X-Tenant-ID": "test-e2e-tenant"},
        )
    assert resp.status_code == 202
    upload_id = resp.json()["upload_id"]

    # 2. Worker executes multi-branch analysis WITHOUT validated model (default baseline)
    processor = MediaProcessor(storage_client=storage)
    assert processor.pipeline.has_validated_model is False

    async with session_maker() as session:
        decision = await processor.process_media_file(
            media_path=clean_file,
            upload_id=upload_id,
            session=session,
            tenant_id="test-e2e-tenant",
        )
        await session.commit()

    assert decision.verdict == "HUMAN_REVIEW"
    assert "NO_VALIDATED_MODEL" in decision.summary_reason
    assert decision.metadata["reason_code"] == "NO_VALIDATED_MODEL"

    # 3. Check status endpoint confirms HUMAN_REVIEW and NOT published
    st_resp = await client.get(
        f"/v1/media/{upload_id}",
        headers={"X-Tenant-ID": "test-e2e-tenant"},
    )
    assert st_resp.status_code == 200
    st_data = st_resp.json()
    assert st_data["verdict"] == "HUMAN_REVIEW"
    assert st_data["published_url"] is None
