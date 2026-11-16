"""
SafeGate Worker Media Processor.
Executes the full pipeline: extraction -> feature extraction -> fusion -> temporal confirmation -> policy -> DB & audit.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ml.detectors.pipeline import MultiBranchPipeline
from ml.fusion.calibrator import ScoreCalibrator
from ml.fusion.temporal_confirmation import TemporalConfirmationEngine
from safegate_api.audit import record_audit_event
from safegate_api.config import settings
from safegate_api.errors import MediaDecodeError
from safegate_api.logging import logger
from safegate_api.models import FrameAnalysis, MediaUpload
from safegate_api.storage import StorageClient
from safegate_worker.extractor import extract_media_frames
from safegate_worker.policy import ContentDecision, ContentPolicyEngine


class MediaProcessor:
    """
    Coordinates extraction, ML inference, calibration, policy, and persistence.
    """

    def __init__(
        self,
        storage_client: StorageClient | None = None,
        pipeline: MultiBranchPipeline | None = None,
    ) -> None:
        self.storage = storage_client or StorageClient(config=settings.storage)
        self.pipeline = pipeline or MultiBranchPipeline()
        self.calibrator = ScoreCalibrator()
        self.confirmation_engine = TemporalConfirmationEngine(thresholds=settings.thresholds)
        self.policy_engine = ContentPolicyEngine()

    async def process_media_file(
        self,
        media_path: Path,
        upload_id: str,
        session: AsyncSession,
        tenant_id: str = "default-tenant",
    ) -> ContentDecision:
        """
        Executes end-to-end processing pipeline on a single media file.
        Enforces fail-closed handling on all exceptions.
        """
        logger.info(f"Beginning media processing for upload '{upload_id}' at {media_path}")
        self.pipeline.reset()

        try:
            # 1 & 2. Streaming batch processing with immediate pixel buffer release
            # Avoids OOM by keeping only 1 raw pixel array in memory at any moment
            fused_frames = []
            frame_gen = extract_media_frames(media_path)

            try:
                first_frame = next(frame_gen)
            except StopIteration:
                raise MediaDecodeError("Media stream contains 0 decodable frames.") from None

            try:
                second_frame = next(frame_gen)
                has_multiple = True
            except StopIteration:
                has_multiple = False
                second_frame = None

            is_single = not has_multiple

            def _process_frame_and_release(fd: Any) -> Any:
                raw_res = self.pipeline.process_frame(
                    rgb_frame=fd.rgb_array,
                    frame_index=fd.frame_index,
                    timestamp_ms=fd.timestamp_ms,
                )
                return self.calibrator.calibrate_and_fuse(raw_res, is_single_frame=is_single)

            fused_frames.append(_process_frame_and_release(first_frame))
            del first_frame

            if second_frame is not None:
                fused_frames.append(_process_frame_and_release(second_frame))
                del second_frame

                for frame_data in frame_gen:
                    fused_frames.append(_process_frame_and_release(frame_data))
                    del frame_data

            # 3. Apply temporal confirmation & color assignment (Rule 7)
            verdicts = self.confirmation_engine.evaluate_sequence(fused_frames)

            # 4. Resolve content-level policy (RED > YELLOW > GREEN) with fail-closed model validation
            decision = self.policy_engine.evaluate(
                frame_verdicts=verdicts,
                detector_type=getattr(self.pipeline, "detector_type", "heuristic"),
                has_validated_model=getattr(self.pipeline, "has_validated_model", False),
                has_calibrated_thresholds=getattr(self.pipeline, "has_calibrated_thresholds", False),
            )

            # 5. Persist per-frame analysis records into database in chunks of 250
            frame_records: list[FrameAnalysis] = [
                FrameAnalysis(
                    upload_id=upload_id,
                    frame_index=v.frame_index,
                    timestamp_ms=v.timestamp_ms,
                    color=v.color,
                    deepfake_score=v.deepfake_score,
                    sensitive_score=v.sensitive_score,
                    uncertainty_score=v.uncertainty_score,
                    cues_json=json.dumps(v.cues),
                )
                for v in verdicts
            ]

            db_chunk_size = 250
            for i in range(0, len(frame_records), db_chunk_size):
                chunk = frame_records[i : i + db_chunk_size]
                session.add_all(chunk)
                await session.flush()

            # 6. Update MediaUpload status and verdict
            stmt = select(MediaUpload).where(MediaUpload.id == upload_id)
            res = await session.execute(stmt)
            upload_entry = res.scalar_one_or_none()

            if upload_entry:
                upload_entry.status = "COMPLETED"
                upload_entry.verdict = decision.verdict
                upload_entry.total_frames = decision.total_frames
                upload_entry.red_frame_count = decision.red_frames
                upload_entry.yellow_frame_count = decision.yellow_frames
                upload_entry.green_frame_count = decision.green_frames
                upload_entry.completed_at = datetime.now(UTC)

                # If cleared ALLOW, promote to published storage
                if decision.verdict == "ALLOW":
                    try:
                        published_uri = self.storage.promote_to_published(
                            key=upload_entry.quarantine_key,
                            allow_confirmed=True,
                        )
                        upload_entry.published_key = published_uri
                    except Exception as stor_err:
                        logger.error(f"Storage promotion failed for upload {upload_id}: {stor_err}")

            # 7. Append immutable audit ledger record
            audit_payload: dict[str, Any] = {
                "verdict": decision.verdict,
                "total_frames": decision.total_frames,
                "red_frames": decision.red_frames,
                "yellow_frames": decision.yellow_frames,
                "green_frames": decision.green_frames,
                "summary": decision.summary_reason,
                "detector_type": getattr(self.pipeline, "detector_type", "heuristic"),
                "model_version": getattr(self.pipeline, "model_version", "0.1.0-heuristic"),
                "model_checksum": getattr(self.pipeline, "model_checksum", None),
                "metadata": decision.metadata,
            }
            await record_audit_event(
                session=session,
                event_type="VERDICT_ISSUED",
                tenant_id=tenant_id,
                upload_id=upload_id,
                payload=audit_payload,
            )

            await session.commit()
            logger.info(
                f"Processing complete for upload '{upload_id}': verdict={decision.verdict} "
                f"(R:{decision.red_frames}, Y:{decision.yellow_frames}, G:{decision.green_frames})"
            )
            return decision

        except Exception as exc:
            # Enforce strict fail-closed fallback
            logger.exception(
                f"Fail-closed triggered during processing of upload '{upload_id}': {exc}"
            )
            fail_decision = self.policy_engine.evaluate(
                frame_verdicts=[],
                fail_closed_triggered=True,
                error_context=str(exc),
            )

            # Mark upload failed/review in database
            stmt = select(MediaUpload).where(MediaUpload.id == upload_id)
            res = await session.execute(stmt)
            upload_entry = res.scalar_one_or_none()
            if upload_entry:
                upload_entry.status = "FAILED"
                upload_entry.verdict = "HUMAN_REVIEW"
                upload_entry.completed_at = datetime.now(UTC)

            await record_audit_event(
                session=session,
                event_type="FAIL_CLOSED_ESCALATION",
                tenant_id=tenant_id,
                upload_id=upload_id,
                payload={"error": str(exc), "verdict": "HUMAN_REVIEW"},
            )
            await session.commit()
            return fail_decision
