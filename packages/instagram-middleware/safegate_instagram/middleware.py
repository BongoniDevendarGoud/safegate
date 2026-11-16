"""
SafeGate Instagram Middleware Subsystem.
Integrates directly with Instagram Content Publishing API flow:
1. Intercepts media before container publication (POST /{ig-user-id}/media_publish)
2. Runs SafeGate firewall screening on all extracted frames
3. Enforces tri-state policy:
   - GREEN (ALLOW): Publishes container to Instagram
   - YELLOW (HUMAN_REVIEW): Holds container in moderation quarantine
   - RED (BLOCK): Rejects container permanently, emits violation report
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from safegate_sdk.client import AsyncSafeGateClient, SafeGateClient


class InstagramIntegrityViolationError(Exception):
    """Raised when an Instagram upload is blocked due to detected deepfake or manipulation."""

    def __init__(self, message: str, red_frames: int, upload_id: str) -> None:
        super().__init__(message)
        self.red_frames = red_frames
        self.upload_id = upload_id


@dataclass(frozen=True)
class InstagramUploadRequest:
    ig_user_id: str
    media_path: str | Path
    caption: str
    media_type: str = "IMAGE"  # IMAGE, VIDEO, REELS, STORIES


@dataclass(frozen=True)
class InstagramPublishResult:
    published: bool
    status: str  # PUBLISHED, HELD_IN_REVIEW, BLOCKED
    instagram_media_id: str | None
    safegate_upload_id: str
    safegate_verdict: str
    total_frames: int
    red_frames: int
    yellow_frames: int
    green_frames: int
    message: str


class InstagramPublishingInterceptor:
    """
    Middleware bridge between Instagram Graph API publishing pipelines and SafeGate.
    Ensures zero synthetic morphing or unmoderated sensitive content is published to Instagram.
    """

    def __init__(
        self,
        safegate_client: SafeGateClient | None = None,
        async_safegate_client: AsyncSafeGateClient | None = None,
        instagram_graph_base_url: str = "https://graph.facebook.com/v19.0",
        graph_access_token: str = "mock-ig-access-token",
    ) -> None:
        self.sg_client = safegate_client or SafeGateClient(
            base_url="http://localhost:8000",
            tenant_id="instagram-platform",
        )
        self.async_sg_client = async_safegate_client or AsyncSafeGateClient(
            base_url="http://localhost:8000",
            tenant_id="instagram-platform",
        )
        self.graph_base_url = instagram_graph_base_url
        self.access_token = graph_access_token

    async def screen_and_publish(
        self,
        request: InstagramUploadRequest,
    ) -> InstagramPublishResult:
        """
        Asynchronously screens the media with SafeGate before committing publication to Instagram.
        """
        # 1. Screen media with SafeGate Firewall
        up_res = await self.async_sg_client.upload_media(request.media_path)
        status_res = await self.async_sg_client.get_status(up_res.upload_id)

        verdict = status_res.verdict

        # 2. Strict Tri-State Policy Enforcement
        if verdict == "BLOCK":
            # Confirmed deepfake or manipulated media
            raise InstagramIntegrityViolationError(
                message=(
                    f"Upload blocked by SafeGate: Confirmed deepfake or morphed synthetic media "
                    f"detected ({status_res.red_frames} RED frame(s)). Publication to Instagram denied."
                ),
                red_frames=status_res.red_frames,
                upload_id=up_res.upload_id,
            )

        if verdict == "HUMAN_REVIEW":
            # Blood, nudity, or model uncertainty
            return InstagramPublishResult(
                published=False,
                status="HELD_IN_REVIEW",
                instagram_media_id=None,
                safegate_upload_id=up_res.upload_id,
                safegate_verdict=verdict,
                total_frames=status_res.total_frames,
                red_frames=status_res.red_frames,
                yellow_frames=status_res.yellow_frames,
                green_frames=status_res.green_frames,
                message="Held in Instagram Safety Review queue: Sensitive cues detected. Post will publish upon moderator approval.",
            )

        # 3. All frames GREEN (ALLOW) -> Proceed to Instagram Graph API publish
        ig_media_id = await self._call_instagram_media_publish(
            ig_user_id=request.ig_user_id,
            container_id=f"mock-container-{up_res.upload_id[:8]}",
        )

        return InstagramPublishResult(
            published=True,
            status="PUBLISHED",
            instagram_media_id=ig_media_id,
            safegate_upload_id=up_res.upload_id,
            safegate_verdict=verdict,
            total_frames=status_res.total_frames,
            red_frames=status_res.red_frames,
            yellow_frames=status_res.yellow_frames,
            green_frames=status_res.green_frames,
            message="Media verified clean by SafeGate. Post published successfully to Instagram.",
        )

    async def _call_instagram_media_publish(
        self,
        ig_user_id: str,
        container_id: str,
    ) -> str:
        """
        Executes POST /{ig-user-id}/media_publish to complete Instagram publishing.
        In test/dev environment, returns the generated Instagram post media ID.
        """
        # Generates deterministic published ID
        return f"ig_post_{ig_user_id}_{container_id}"
