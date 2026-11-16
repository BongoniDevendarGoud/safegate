"""Unit tests for SafeGate Instagram publishing middleware."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from safegate_instagram.middleware import (
    InstagramIntegrityViolationError,
    InstagramPublishingInterceptor,
    InstagramUploadRequest,
)
from safegate_sdk.client import AsyncSafeGateClient, StatusResult, UploadResult


@pytest.mark.asyncio
async def test_instagram_middleware_cleans_and_publishes(tmp_path: Path) -> None:
    """Verifies that authentic media passes SafeGate and publishes to Instagram."""
    mock_file = tmp_path / "insta_clean.jpg"
    mock_file.write_bytes(b"\xff\xd8\xff" + b"\x00" * 30)

    mock_sg = AsyncMock(spec=AsyncSafeGateClient)
    mock_sg.upload_media.return_value = UploadResult(
        upload_id="ig-up-001",
        tenant_id="instagram-platform",
        filename="insta_clean.jpg",
        mime_type="image/jpeg",
        file_size_bytes=33,
        sha256_hash="abc123clean",
        status="QUEUED",
        verdict="PENDING",
        message="Quarantined",
    )
    mock_sg.get_status.return_value = StatusResult(
        upload_id="ig-up-001",
        tenant_id="instagram-platform",
        filename="insta_clean.jpg",
        status="COMPLETED",
        verdict="ALLOW",
        total_frames=1,
        red_frames=0,
        yellow_frames=0,
        green_frames=1,
        published_url="s3://pub/clean.jpg",
        raw_data={},
    )

    interceptor = InstagramPublishingInterceptor(async_safegate_client=mock_sg)
    req = InstagramUploadRequest(
        ig_user_id="17841400000000001",
        media_path=mock_file,
        caption="Beautiful sunset on Instagram! 🌅",
    )

    res = await interceptor.screen_and_publish(req)
    assert res.published is True
    assert res.status == "PUBLISHED"
    assert res.instagram_media_id is not None
    assert "ig_post_" in res.instagram_media_id
    assert res.green_frames == 1


@pytest.mark.asyncio
async def test_instagram_middleware_sensitive_routes_to_review(tmp_path: Path) -> None:
    """Verifies that blood/sensitive media is held in review and NOT published to Instagram."""
    mock_file = tmp_path / "insta_blood.jpg"
    mock_file.write_bytes(b"\xff\xd8\xff" + b"\x00" * 30)

    mock_sg = AsyncMock(spec=AsyncSafeGateClient)
    mock_sg.upload_media.return_value = UploadResult(
        upload_id="ig-up-002",
        tenant_id="instagram-platform",
        filename="insta_blood.jpg",
        mime_type="image/jpeg",
        file_size_bytes=33,
        sha256_hash="abc123blood",
        status="QUEUED",
        verdict="PENDING",
        message="Quarantined",
    )
    mock_sg.get_status.return_value = StatusResult(
        upload_id="ig-up-002",
        tenant_id="instagram-platform",
        filename="insta_blood.jpg",
        status="COMPLETED",
        verdict="HUMAN_REVIEW",
        total_frames=1,
        red_frames=0,
        yellow_frames=1,
        green_frames=0,
        published_url=None,
        raw_data={},
    )

    interceptor = InstagramPublishingInterceptor(async_safegate_client=mock_sg)
    req = InstagramUploadRequest(
        ig_user_id="17841400000000001",
        media_path=mock_file,
        caption="Movie set scene with prop blood! 🎬",
    )

    res = await interceptor.screen_and_publish(req)
    assert res.published is False
    assert res.status == "HELD_IN_REVIEW"
    assert res.instagram_media_id is None
    assert res.yellow_frames == 1


@pytest.mark.asyncio
async def test_instagram_middleware_blocks_deepfake_morph(tmp_path: Path) -> None:
    """Verifies that deepfake / morphed media is BLOCKED and raises integrity violation."""
    mock_file = tmp_path / "insta_deepfake.mp4"
    mock_file.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 30)

    mock_sg = AsyncMock(spec=AsyncSafeGateClient)
    mock_sg.upload_media.return_value = UploadResult(
        upload_id="ig-up-003",
        tenant_id="instagram-platform",
        filename="insta_deepfake.mp4",
        mime_type="video/mp4",
        file_size_bytes=38,
        sha256_hash="abc123fake",
        status="QUEUED",
        verdict="PENDING",
        message="Quarantined",
    )
    mock_sg.get_status.return_value = StatusResult(
        upload_id="ig-up-003",
        tenant_id="instagram-platform",
        filename="insta_deepfake.mp4",
        status="COMPLETED",
        verdict="BLOCK",
        total_frames=30,
        red_frames=4,
        yellow_frames=0,
        green_frames=26,
        published_url=None,
        raw_data={},
    )

    interceptor = InstagramPublishingInterceptor(async_safegate_client=mock_sg)
    req = InstagramUploadRequest(
        ig_user_id="17841400000000001",
        media_path=mock_file,
        caption="Fake video test!",
    )

    with pytest.raises(InstagramIntegrityViolationError) as exc_info:
        await interceptor.screen_and_publish(req)

    assert exc_info.value.red_frames == 4
    assert "Publication to Instagram denied" in str(exc_info.value)
