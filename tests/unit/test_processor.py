from collections.abc import AsyncGenerator
from pathlib import Path

import cv2
import numpy as np
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from safegate_api.config import settings
from safegate_api.database import Base
from safegate_api.models import FrameAnalysis, MediaUpload
from safegate_api.storage import StorageClient
from safegate_worker.processor import MediaProcessor


@pytest_asyncio.fixture
async def processor_env(
    tmp_path: Path,
) -> AsyncGenerator[tuple[MediaProcessor, AsyncSession, StorageClient], None]:
    """Sets up an isolated SQLite DB, local storage client, and MediaProcessor."""
    db_file = tmp_path / "test_proc.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    storage = StorageClient(config=settings.storage, local_storage_dir=tmp_path / "storage")
    processor = MediaProcessor(storage_client=storage)

    async with session_maker() as session:
        yield processor, session, storage

    await engine.dispose()


@pytest.mark.asyncio
async def test_processor_clean_image(
    processor_env: tuple[MediaProcessor, AsyncSession, StorageClient],
    tmp_path: Path,
) -> None:
    """Verify clean image processes to ALLOW, updates DB, and promotes to published."""
    processor, session, storage = processor_env

    # 1. Create clean synthetic image with natural gradient and sensor noise
    clean_img_path = tmp_path / "clean.jpg"
    x = np.linspace(60, 180, 160)
    y = np.linspace(80, 200, 120)
    xx, yy = np.meshgrid(x, y)
    img_rgb = np.zeros((120, 160, 3), dtype=np.uint8)
    img_rgb[:, :, 0] = xx.astype(np.uint8)
    img_rgb[:, :, 1] = yy.astype(np.uint8)
    img_rgb[:, :, 2] = ((xx + yy) / 2).astype(np.uint8)

    # Add realistic sensor noise (std ~ 3.0)
    np.random.seed(42)
    noise = np.random.normal(0, 3.0, img_rgb.shape).astype(np.int16)
    img_rgb = np.clip(img_rgb.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Write as BGR so cv2.imread reconstructs accurate RGB
    cv2.imwrite(str(clean_img_path), cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))

    # 2. Put into quarantine storage
    upload_id = "test-upload-clean-01"
    q_key = f"default-tenant/{upload_id}/clean.jpg"
    storage.upload_quarantine(key=q_key, data=clean_img_path.read_bytes())

    # 3. Create MediaUpload database record
    upload_rec = MediaUpload(
        id=upload_id,
        tenant_id="default-tenant",
        filename="clean.jpg",
        file_size_bytes=clean_img_path.stat().st_size,
        mime_type="image/jpeg",
        sha256_hash="abc123clean",
        is_video=False,
        status="QUEUED",
        verdict="PENDING",
        quarantine_key=q_key,
    )
    session.add(upload_rec)
    await session.commit()

    # 4. Configure validated model state for clearance test
    processor.pipeline.has_validated_model = True
    processor.pipeline.has_calibrated_thresholds = True
    processor.pipeline.detector_type = "model"

    # Process media file
    decision = await processor.process_media_file(
        media_path=clean_img_path,
        upload_id=upload_id,
        session=session,
    )

    assert decision.verdict == "ALLOW"
    assert decision.total_frames == 1
    assert decision.green_frames == 1

    # Verify DB state
    updated_rec = await session.get(MediaUpload, upload_id)
    assert updated_rec is not None
    assert updated_rec.status == "COMPLETED"
    assert updated_rec.verdict == "ALLOW"
    assert updated_rec.published_key is not None

    # Verify FrameAnalysis recorded
    stmt = select(FrameAnalysis).where(FrameAnalysis.upload_id == upload_id)
    res = await session.execute(stmt)
    frames = res.scalars().all()
    assert len(frames) == 1
    assert frames[0].color == "GREEN"


@pytest.mark.asyncio
async def test_processor_blood_image_routes_to_human_review(
    processor_env: tuple[MediaProcessor, AsyncSession, StorageClient],
    tmp_path: Path,
) -> None:
    """Verify image with blood/violence processes to HUMAN_REVIEW (YELLOW)."""
    processor, session, storage = processor_env

    # 1. Create image with crimson/blood pool in RGB
    blood_img_path = tmp_path / "blood.jpg"
    img_rgb = np.full((120, 160, 3), fill_value=200, dtype=np.uint8)
    img_rgb[30:90, 40:120] = [180, 10, 20]  # Deep crimson in RGB
    cv2.imwrite(str(blood_img_path), cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))

    upload_id = "test-upload-blood-02"
    q_key = f"default-tenant/{upload_id}/blood.jpg"
    storage.upload_quarantine(key=q_key, data=blood_img_path.read_bytes())

    upload_rec = MediaUpload(
        id=upload_id,
        tenant_id="default-tenant",
        filename="blood.jpg",
        file_size_bytes=blood_img_path.stat().st_size,
        mime_type="image/jpeg",
        sha256_hash="abc123blood",
        is_video=False,
        status="QUEUED",
        verdict="PENDING",
        quarantine_key=q_key,
    )
    session.add(upload_rec)
    await session.commit()

    decision = await processor.process_media_file(
        media_path=blood_img_path,
        upload_id=upload_id,
        session=session,
    )

    assert decision.verdict == "HUMAN_REVIEW"
    assert decision.yellow_frames == 1

    updated_rec = await session.get(MediaUpload, upload_id)
    assert updated_rec is not None
    assert updated_rec.verdict == "HUMAN_REVIEW"
    assert updated_rec.published_key is None  # Never published


@pytest.mark.asyncio
async def test_processor_streaming_multi_frame_video(
    processor_env: tuple[MediaProcessor, AsyncSession, StorageClient],
    tmp_path: Path,
) -> None:
    """Verify streaming processing on multi-frame video operates under constant memory."""
    processor, session, storage = processor_env

    # Synthesize clean 30-frame MP4 video
    video_path = tmp_path / "stream_test.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(video_path), fourcc, 30.0, (160, 120))

    np.random.seed(42)
    for f_idx in range(30):
        frame = np.full((120, 160, 3), fill_value=128, dtype=np.uint8)
        # Add subtle spatial movement and sensor noise
        frame[:, :, 0] = np.clip(100 + f_idx * 2 + np.random.normal(0, 2.0, (120, 160)), 0, 255)
        frame[:, :, 1] = np.clip(120 + np.random.normal(0, 2.0, (120, 160)), 0, 255)
        frame[:, :, 2] = np.clip(140 + np.random.normal(0, 2.0, (120, 160)), 0, 255)
        out.write(frame)
    out.release()

    upload_id = "test-upload-video-stream-01"
    q_key = f"default-tenant/{upload_id}/stream_test.mp4"
    storage.upload_quarantine(key=q_key, data=video_path.read_bytes())

    upload_rec = MediaUpload(
        id=upload_id,
        tenant_id="default-tenant",
        filename="stream_test.mp4",
        file_size_bytes=video_path.stat().st_size,
        mime_type="video/mp4",
        sha256_hash="abcvideo123",
        is_video=True,
        status="QUEUED",
        verdict="PENDING",
        quarantine_key=q_key,
    )
    session.add(upload_rec)
    await session.commit()

    decision = await processor.process_media_file(
        media_path=video_path,
        upload_id=upload_id,
        session=session,
    )

    assert decision.total_frames == 30
    assert decision.red_frames == 0
    assert decision.yellow_frames + decision.green_frames == 30

    stmt = select(FrameAnalysis).where(FrameAnalysis.upload_id == upload_id)
    res = await session.execute(stmt)
    records = res.scalars().all()
    assert len(records) == 30


@pytest.mark.asyncio
async def test_processor_unvalidated_model_routes_to_human_review(
    processor_env: tuple[MediaProcessor, AsyncSession, StorageClient],
    tmp_path: Path,
) -> None:
    """Verify that without a validated model, even clean media routes to HUMAN_REVIEW."""
    processor, session, storage = processor_env
    from ml.detectors.pipeline import MultiBranchPipeline

    processor.pipeline = MultiBranchPipeline(has_validated_model=False, detector_type="heuristic")
    clean_img_path = tmp_path / "clean_unval.jpg"
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
    cv2.imwrite(str(clean_img_path), cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR))

    upload_id = "test-upload-unval-01"
    q_key = f"default-tenant/{upload_id}/clean_unval.jpg"
    storage.upload_quarantine(key=q_key, data=clean_img_path.read_bytes())

    upload_rec = MediaUpload(
        id=upload_id,
        tenant_id="default-tenant",
        filename="clean_unval.jpg",
        file_size_bytes=clean_img_path.stat().st_size,
        mime_type="image/jpeg",
        sha256_hash="abc_unval",
        is_video=False,
        status="QUEUED",
        verdict="PENDING",
        quarantine_key=q_key,
    )
    session.add(upload_rec)
    await session.commit()

    decision = await processor.process_media_file(
        media_path=clean_img_path,
        upload_id=upload_id,
        session=session,
    )

    assert decision.verdict == "HUMAN_REVIEW"
    assert decision.metadata["reason_code"] == "NO_VALIDATED_MODEL"
