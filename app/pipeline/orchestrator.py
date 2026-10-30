"""
SafeGate — Screening Pipeline Orchestrator
===========================================
Coordinates the sequential execution of every screening stage for an upload:

PIPELINE EXECUTION ORDER:
Stage 1: Intake & Quarantine (completed prior to orchestration)
Stage 2: Exact Cryptographic Hash (SHA-256 vs blocklist_hashes) -> Match = Fast BLOCK
Stage 3: Video Frame Extraction (OpenCV: 1 frame / 2s + first + last)
Stage 4: Perceptual Hash (pHash vs blocklist_phashes) -> Match = Fast BLOCK
Stage 5: Local NSFW Model Inference (Falconsai/nsfw_image_detection)
Stage 6: Gemini AI Second-Opinion (borderline frames only; integrated in Phase 3)
Stage 7: Deepfake Heuristics (blur/flicker/metadata analysis; integrated in Phase 3)
Stage 8: Decision Engine Evaluation (emits BLOCK, REVIEW, or ALLOW)

MEDIA LIFECYCLE ON VERDICT:
- BLOCK:
  1. Unlink (destroy) the video file immediately from disk (defensive rule).
  2. Index its SHA-256 and all frame pHashes into blocklist tables.
  3. Persist explanation and scores to the database.
- REVIEW:
  1. Move file from quarantine/ to review/ for moderator investigation.
  2. Persist decision details.
- ALLOW:
  1. Move file from quarantine/ to published/.
  2. Persist decision details.

FAIL-CLOSED GUARANTEE:
Any unhandled exception, model failure, or timeout in any stage automatically
assigns verdict="REVIEW", ensuring prohibited content is NEVER mistakenly allowed.
"""

import logging
import shutil
import time
from pathlib import Path
from sqlalchemy.orm import Session
from app.config import settings
from app.models.database import Upload
from app.pipeline.intake import cleanup_file
from app.pipeline.hashing import (
    compute_sha256,
    check_exact_blocklist,
    add_to_exact_blocklist,
    compute_all_phashes,
    check_perceptual_blocklist,
    add_to_perceptual_blocklist,
)
from app.pipeline.frame_extraction import extract_video_frames
from app.pipeline.nsfw_detector import score_frames
from app.pipeline.gemini_opinion import is_borderline, query_gemini_second_opinion
from app.pipeline.deepfake_detector import calculate_deepfake_risk
from app.pipeline.decision import ScreeningSignals, evaluate_signals, DecisionResult

logger = logging.getLogger(__name__)


def run_pipeline(upload_id: str, file_path: Path, db: Session) -> Upload:
    """
    Executes the SafeGate screening pipeline on a quarantined video file.

    Args:
        upload_id: Database UUID of the upload record.
        file_path: Filesystem path to the quarantined video file.
        db: SQLAlchemy database session.

    Returns:
        Updated Upload database record.
    """
    start_time = time.time()
    logger.info(">>> Starting SafeGate Pipeline for Upload ID: %s (file: %s)", upload_id, file_path.name)

    upload_record = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload_record:
        raise ValueError(f"Upload record '{upload_id}' not found in database")

    signals = ScreeningSignals()
    raw_bytes = None
    all_frame_phashes = []

    try:
        # ---------------------------------------------------------------------
        # Stage 2: Exact SHA-256 Cryptographic Hash Check
        # ---------------------------------------------------------------------
        raw_bytes = file_path.read_bytes()
        sha256_hash = compute_sha256(raw_bytes)
        upload_record.sha256_hash = sha256_hash
        db.commit()

        if check_exact_blocklist(sha256_hash, db):
            signals.exact_match = True
            logger.warning("Stage 2 Triggered: Exact hash match for upload %s", upload_id)
            decision = evaluate_signals(signals)
            return _finalize_decision(upload_record, decision, file_path, sha256_hash, [], db, start_time)

        # ---------------------------------------------------------------------
        # Stage 3: Video Frame Extraction
        # ---------------------------------------------------------------------
        frames = extract_video_frames(file_path)

        # ---------------------------------------------------------------------
        # Stage 4: Perceptual Hashing (pHash) Deduplication
        # ---------------------------------------------------------------------
        frame_phashes_with_ts = compute_all_phashes(frames)
        all_frame_phashes = [ph for _, ph in frame_phashes_with_ts]

        phash_match = check_perceptual_blocklist(frame_phashes_with_ts, db)
        if phash_match:
            ts, frame_ph, block_ph, dist = phash_match
            signals.perceptual_match = {
                "timestamp": ts,
                "frame_phash": frame_ph,
                "block_phash": block_ph,
                "distance": dist,
            }
            logger.warning("Stage 4 Triggered: Perceptual match for upload %s", upload_id)
            decision = evaluate_signals(signals)
            return _finalize_decision(upload_record, decision, file_path, sha256_hash, all_frame_phashes, db, start_time)

        # ---------------------------------------------------------------------
        # Stage 5: Local NSFW Vision Model Inference
        # ---------------------------------------------------------------------
        worst_score, worst_ts, _ = score_frames(frames)
        signals.nsfw_worst_score = worst_score
        signals.nsfw_worst_timestamp = worst_ts
        upload_record.nsfw_worst_score = worst_score
        upload_record.nsfw_worst_timestamp = worst_ts
        db.commit()

        # ---------------------------------------------------------------------
        # Stage 6: Gemini AI Second-Opinion (Borderline NSFW Only)
        # ---------------------------------------------------------------------
        if is_borderline(worst_score):
            # Locate the specific frame corresponding to the peak borderline score
            borderline_frame = None
            for ts, img in frames:
                if abs(ts - worst_ts) < 0.05:
                    borderline_frame = img
                    break
            if borderline_frame is None and frames:
                borderline_frame = frames[0][1]

            logger.info("Stage 6: Querying Gemini for borderline frame at %.2fs (score=%.4f)...", worst_ts, worst_score)
            gemini_out = query_gemini_second_opinion(borderline_frame, worst_ts)
            signals.gemini_explicit = gemini_out.get("explicit")
            signals.gemini_confidence = gemini_out.get("confidence", 0.0)
            signals.gemini_reason = gemini_out.get("reason")
            upload_record.gemini_result = gemini_out.get("raw_response")
            db.commit()

        # ---------------------------------------------------------------------
        # Stage 7: Probabilistic Deepfake Risk Assessment
        # ---------------------------------------------------------------------
        df_score, df_reasons = calculate_deepfake_risk(file_path, frames)
        signals.deepfake_score = df_score
        signals.deepfake_reasons = df_reasons
        upload_record.deepfake_risk_score = df_score
        if df_reasons:
            import json
            upload_record.deepfake_reasons = json.dumps(df_reasons)
        db.commit()

        # ---------------------------------------------------------------------
        # Stage 8: Decision Engine Evaluation
        # ---------------------------------------------------------------------
        decision = evaluate_signals(signals)

    except Exception as exc:
        logger.error("Pipeline failure on upload %s: %s", upload_id, exc, exc_info=True)
        signals.stage_error = str(exc)
        decision = evaluate_signals(signals)

    # Apply physical file routing and finalize records
    sha_to_store = upload_record.sha256_hash or (compute_sha256(raw_bytes) if raw_bytes else None)
    return _finalize_decision(upload_record, decision, file_path, sha_to_store, all_frame_phashes, db, start_time)


def _finalize_decision(
    upload_record: Upload,
    decision: DecisionResult,
    file_path: Path,
    sha256_hash: str,
    all_frame_phashes: list,
    db: Session,
    start_time: float,
) -> Upload:
    """
    Applies the physical file operations (destroy, move to review, or publish),
    updates the database record, and records blocklist fingerprints when content is BLOCKED.
    """
    duration = round(time.time() - start_time, 4)
    upload_record.verdict = decision.verdict
    upload_record.explanation = decision.explanation
    upload_record.scan_duration_sec = duration

    logger.info(
        "=== Verdict for %s: %s (duration=%.3fs) — Reason: %s ===",
        upload_record.id, decision.verdict, duration, decision.explanation
    )

    try:
        if decision.verdict == "BLOCK":
            # Defensive rule: delete the physical media file immediately
            cleanup_file(file_path)
            upload_record.stored_filename = "DELETED_ON_BLOCK"

            # Retain non-reversible fingerprints in blocklist tables
            if sha256_hash:
                add_to_exact_blocklist(sha256_hash, db, source=f"auto-block-{decision.triggered_stage}")
            if all_frame_phashes:
                add_to_perceptual_blocklist(all_frame_phashes, db, source=f"auto-block-{decision.triggered_stage}")

        elif decision.verdict == "REVIEW":
            # Move from quarantine/ to review/
            settings.review_path.mkdir(parents=True, exist_ok=True)
            target_path = settings.review_path / file_path.name
            if file_path.exists():
                shutil.move(str(file_path), str(target_path))
                logger.info("Moved upload %s to %s", upload_record.id, target_path)

        elif decision.verdict == "ALLOW":
            # Move from quarantine/ to published/
            settings.published_path.mkdir(parents=True, exist_ok=True)
            target_path = settings.published_path / file_path.name
            if file_path.exists():
                shutil.move(str(file_path), str(target_path))
                logger.info("Published upload %s to %s", upload_record.id, target_path)

    except Exception as move_err:
        logger.error("Error during file relocation for %s: %s", upload_record.id, move_err)
        # Fail-closed guarantee
        upload_record.verdict = "REVIEW"
        upload_record.explanation = f"Fail-closed: File relocation failed ({move_err})"

    db.commit()
    db.refresh(upload_record)
    return upload_record
