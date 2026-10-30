"""
SafeGate OSI Model — Unified 7-Layer Protocol Stack Coordinator
================================================================
Implements the complete 7-Layer OSI Architecture for fail-closed video screening:
- Layer 1 (Physical): Raw byte streaming, memory bounds, size enforcement.
- Layer 2 (Data Link): Video frame delineation, temporal sampling, time sync.
- Layer 3 (Network): Client IP origin tracking, rate limiting, traffic policing.
- Layer 4 (Transport): End-to-end SHA-256 integrity checksum & exact blocklist.
- Layer 5 (Session): Constant-time credential authentication & tamper-evident audit hash chaining.
- Layer 6 (Presentation): Magic-byte syntax parsing, transcoding, DCT perceptual hashing.
- Layer 7 (Application): Cognitive AI vision, Gemini consultation, deepfake heuristics & policy gate.

VIVA EXPLANATION:
Why is an OSI-layered design superior for security gateways?
1. Modular Separation of Concerns: Low-level attacks (e.g. malformed bitstreams or IP floods)
   are stopped at Layers 1-3 before expensive deep learning inference is invoked at Layer 7.
2. Defense-in-Depth: Multiple independent checkpoints (Layer 4 SHA-256, Layer 6 pHash,
   Layer 7 AI model) ensure that evasion of one layer is caught by another.
3. Strict Fail-Closed Guarantees: An anomaly at ANY layer aborts transit and drops the packet
   into quarantine/review.
"""

import time
import shutil
import uuid
from pathlib import Path
from dataclasses import dataclass, field
from typing import BinaryIO, Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import Upload, BlocklistHash, BlocklistPHash
from app.pipeline.decision import ScreeningSignals

from app.osi.layer1_physical import Layer1PhysicalBitstream
from app.osi.layer2_datalink import Layer2DataLinkFraming
from app.osi.layer3_network import Layer3NetworkPolicy
from app.osi.layer4_transport import Layer4TransportIntegrity
from app.osi.layer5_session import Layer5SessionControl
from app.osi.layer6_presentation import Layer6PresentationSyntax
from app.osi.layer7_application import Layer7ApplicationPolicy


@dataclass
class LayerExecutionStep:
    layer_num: int
    layer_name: str
    status: str  # "PASS", "FAIL", "BLOCKED", "REVIEW"
    details: str
    duration_ms: float


@dataclass
class OSIStackReport:
    upload_id: str
    verdict: str  # "ALLOW", "REVIEW", "BLOCK"
    explanation: str
    scan_duration_sec: float
    sha256_hash: Optional[str] = None
    nsfw_worst_score: Optional[float] = None
    deepfake_risk_score: Optional[int] = None
    steps: List[LayerExecutionStep] = field(default_factory=list)


class OSIProtocolStack:
    """
    Coordinates packet traversal across all 7 layers of the SafeGate OSI Architecture.
    """

    def __init__(self):
        self.l1 = Layer1PhysicalBitstream()
        self.l2 = Layer2DataLinkFraming()
        self.l3 = Layer3NetworkPolicy()
        self.l4 = Layer4TransportIntegrity()
        self.l5 = Layer5SessionControl()
        self.l6 = Layer6PresentationSyntax()
        self.l7 = Layer7ApplicationPolicy()

    def process_media_stream(
        self,
        stream: BinaryIO,
        original_filename: str,
        client_ip: str,
        session_key: str,
        db: Session,
        required_role: str = "client",
    ) -> OSIStackReport:
        """
        Executes an incoming media stream across Layers 1 through 7 sequentially.
        """
        t0 = time.time()
        upload_id = uuid.uuid4().hex
        steps: List[LayerExecutionStep] = []
        quarantine_file: Optional[Path] = None

        # ---------------------------------------------------------------------
        # LAYER 5: Session Authentication
        # ---------------------------------------------------------------------
        s_t0 = time.time()
        auth_ok, auth_msg = self.l5.authenticate_session(session_key, required_role=required_role)
        steps.append(LayerExecutionStep(5, "Session (Authentication)", "PASS" if auth_ok else "FAIL", auth_msg, (time.time() - s_t0) * 1000))
        if not auth_ok:
            return self._abort(upload_id, "BLOCK", auth_msg, t0, steps)

        # ---------------------------------------------------------------------
        # LAYER 3: Network Policy & Rate Limiting
        # ---------------------------------------------------------------------
        s_t0 = time.time()
        net_ok, net_msg = self.l3.verify_network_origin(client_ip)
        steps.append(LayerExecutionStep(3, "Network (Traffic Policing)", "PASS" if net_ok else "FAIL", net_msg, (time.time() - s_t0) * 1000))
        if not net_ok:
            return self._abort(upload_id, "BLOCK", net_msg, t0, steps)

        # ---------------------------------------------------------------------
        # LAYER 1: Physical Bitstream Reception & Buffering
        # ---------------------------------------------------------------------
        s_t0 = time.time()
        try:
            raw_bytes, total_bytes = self.l1.process_stream(stream, original_filename)
            steps.append(LayerExecutionStep(1, "Physical (Bitstream Ingestion)", "PASS", f"Stream buffered safely ({total_bytes} bytes).", (time.time() - s_t0) * 1000))
        except Exception as exc:
            msg = f"[L1 Physical Error] {exc}"
            steps.append(LayerExecutionStep(1, "Physical (Bitstream Ingestion)", "FAIL", msg, (time.time() - s_t0) * 1000))
            return self._abort(upload_id, "BLOCK", msg, t0, steps)

        # ---------------------------------------------------------------------
        # LAYER 6: Presentation Syntax (Magic Bytes & Container Format)
        # ---------------------------------------------------------------------
        s_t0 = time.time()
        syntax_ok, mime, ext = self.l6.verify_syntax(raw_bytes, original_filename)
        if not syntax_ok:
            msg = f"[L6 Syntax Error] {mime}"
            steps.append(LayerExecutionStep(6, "Presentation (Syntax Validation)", "FAIL", msg, (time.time() - s_t0) * 1000))
            return self._abort(upload_id, "BLOCK", msg, t0, steps)
        steps.append(LayerExecutionStep(6, "Presentation (Syntax Validation)", "PASS", f"MIME format confirmed: {mime} (.{ext})", (time.time() - s_t0) * 1000))

        # ---------------------------------------------------------------------
        # LAYER 4: Transport Integrity Checksum & Exact Hash Blocklist
        # ---------------------------------------------------------------------
        s_t0 = time.time()
        sha256 = self.l4.compute_checksum(raw_bytes)
        t_clean, t_msg = self.l4.verify_transport_blocklist(sha256, db)
        if not t_clean:
            steps.append(LayerExecutionStep(4, "Transport (Integrity & Exact Match)", "BLOCKED", t_msg, (time.time() - s_t0) * 1000))
            return self._finalize_block(upload_id, original_filename, total_bytes, sha256, t_msg, t0, steps, db)
        steps.append(LayerExecutionStep(4, "Transport (Integrity & Exact Match)", "PASS", f"SHA-256 clean: {sha256[:16]}...", (time.time() - s_t0) * 1000))

        # Write to isolated quarantine storage for frame extraction
        stored_name = f"{upload_id}.{ext}"
        quarantine_file = settings.quarantine_path / stored_name
        settings.quarantine_path.mkdir(parents=True, exist_ok=True)
        quarantine_file.write_bytes(raw_bytes)

        # ---------------------------------------------------------------------
        # LAYER 2: Data Link Framing (Temporal Sampling & Frame Extraction)
        # ---------------------------------------------------------------------
        s_t0 = time.time()
        try:
            frames = self.l2.extract_frames(quarantine_file)
            steps.append(LayerExecutionStep(2, "Data Link (Temporal Framing)", "PASS", f"Extracted {len(frames)} synchronized frames.", (time.time() - s_t0) * 1000))
        except Exception as exc:
            msg = f"[L2 Framing Error] Failed to decode frames: {exc}"
            steps.append(LayerExecutionStep(2, "Data Link (Temporal Framing)", "REVIEW", msg, (time.time() - s_t0) * 1000))
            return self._finalize_review(upload_id, original_filename, stored_name, total_bytes, sha256, quarantine_file, msg, t0, steps, db)

        # ---------------------------------------------------------------------
        # LAYER 6: Presentation Frequency Encoding (pHash & Hamming Distance)
        # ---------------------------------------------------------------------
        s_t0 = time.time()
        frame_phashes = self.l6.encode_perceptual_hashes(frames)
        p_clean, matched_ph, p_msg = self.l6.verify_perceptual_blocklist(frame_phashes, db)
        if not p_clean:
            steps.append(LayerExecutionStep(6, "Presentation (pHash Deduplication)", "BLOCKED", p_msg, (time.time() - s_t0) * 1000))
            if quarantine_file and quarantine_file.exists():
                quarantine_file.unlink(missing_ok=True)
            return self._finalize_block(upload_id, original_filename, total_bytes, sha256, p_msg, t0, steps, db)
        steps.append(LayerExecutionStep(6, "Presentation (pHash Deduplication)", "PASS", f"Computed {len(frame_phashes)} frame pHashes. Blocklist clean.", (time.time() - s_t0) * 1000))

        # ---------------------------------------------------------------------
        # LAYER 7: Application AI Policy & Decision Gate
        # ---------------------------------------------------------------------
        s_t0 = time.time()
        worst_score, worst_time, frame_scores = self.l7.classify_nsfw_frames(frames)
        gemini_explicit = None
        gemini_conf = 0.0
        gemini_reason = None
        if settings.REVIEW_THRESHOLD <= worst_score < settings.BLOCK_THRESHOLD:
            worst_frame = next((img for t, img in frames if abs(t - worst_time) < 0.001), frames[0][1])
            gem_res = self.l7.request_cloud_opinion(worst_frame, worst_time)
            if gem_res:
                gemini_explicit = gem_res.get("explicit")
                gemini_conf = gem_res.get("confidence", 0.0)
                gemini_reason = gem_res.get("reason")

        deepfake_risk, deepfake_reasons = self.l7.evaluate_synthetic_manipulation(quarantine_file, frames)

        signals = ScreeningSignals(
            exact_match=False,
            perceptual_match=None,
            nsfw_worst_score=worst_score,
            nsfw_worst_timestamp=worst_time,
            gemini_explicit=gemini_explicit,
            gemini_confidence=gemini_conf,
            gemini_reason=gemini_reason,
            deepfake_score=deepfake_risk,
            deepfake_reasons=deepfake_reasons,
        )

        decision = self.l7.execute_policy_decision(signals)
        verdict = decision.verdict
        explanation = decision.explanation
        steps.append(LayerExecutionStep(
            7,
            "Application (Cognitive Policy Gate)",
            verdict,
            f"NSFW: {worst_score:.2f}, Deepfake: {deepfake_risk}/100 -> {verdict}",
            (time.time() - s_t0) * 1000,
        ))

        # Storage & Audit Enforcement
        scan_time = round(time.time() - t0, 3)

        if verdict == "ALLOW":
            dst = settings.published_path / stored_name
            settings.published_path.mkdir(parents=True, exist_ok=True)
            shutil.move(str(quarantine_file), str(dst))
        elif verdict == "REVIEW":
            dst = settings.review_path / stored_name
            settings.review_path.mkdir(parents=True, exist_ok=True)
            shutil.move(str(quarantine_file), str(dst))
        elif verdict == "BLOCK":
            if quarantine_file.exists():
                quarantine_file.unlink(missing_ok=True)
            # Index hashes in blocklists
            db.add(BlocklistHash(sha256_hash=sha256, source="auto-block"))
            for _, h in frame_phashes:
                db.add(BlocklistPHash(phash_hex=h, source="auto-block"))

        # Commit upload record to SQLite
        upload_record = Upload(
            id=upload_id,
            original_filename=original_filename,
            stored_filename=stored_name,
            file_size=total_bytes,
            sha256_hash=sha256,
            verdict=verdict,
            explanation=explanation,
            nsfw_worst_score=worst_score,
            nsfw_worst_timestamp=worst_time,
            deepfake_risk_score=deepfake_risk,
            scan_duration_sec=scan_time,
        )
        db.add(upload_record)

        # LAYER 5: Session Audit Logging
        self.l5.log_session_event(
            action=f"osi_verdict_{verdict.lower()}",
            details={"verdict": verdict, "sha256": sha256, "latency": scan_time},
            upload_id=upload_id,
            db=db,
        )
        db.commit()

        return OSIStackReport(
            upload_id=upload_id,
            verdict=verdict,
            explanation=explanation,
            scan_duration_sec=scan_time,
            sha256_hash=sha256,
            nsfw_worst_score=worst_score,
            deepfake_risk_score=deepfake_risk,
            steps=steps,
        )

    def _abort(self, upload_id: str, verdict: str, explanation: str, t0: float, steps: List[LayerExecutionStep]) -> OSIStackReport:
        return OSIStackReport(
            upload_id=upload_id,
            verdict=verdict,
            explanation=explanation,
            scan_duration_sec=round(time.time() - t0, 3),
            steps=steps,
        )

    def _finalize_block(self, upload_id, filename, size, sha256, explanation, t0, steps, db) -> OSIStackReport:
        scan_time = round(time.time() - t0, 3)
        u = Upload(id=upload_id, original_filename=filename, stored_filename=f"{upload_id}.bin", file_size=size, sha256_hash=sha256, verdict="BLOCK", explanation=explanation, scan_duration_sec=scan_time)
        db.add(u)
        self.l5.log_session_event("osi_verdict_block", {"sha256": sha256, "explanation": explanation}, upload_id, db)
        db.commit()
        return OSIStackReport(upload_id=upload_id, verdict="BLOCK", explanation=explanation, scan_duration_sec=scan_time, sha256_hash=sha256, steps=steps)

    def _finalize_review(self, upload_id, filename, stored_name, size, sha256, src, explanation, t0, steps, db) -> OSIStackReport:
        scan_time = round(time.time() - t0, 3)
        dst = settings.review_path / stored_name
        settings.review_path.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.move(str(src), str(dst))
        u = Upload(id=upload_id, original_filename=filename, stored_filename=stored_name, file_size=size, sha256_hash=sha256, verdict="REVIEW", explanation=explanation, scan_duration_sec=scan_time)
        db.add(u)
        self.l5.log_session_event("osi_verdict_review", {"sha256": sha256, "explanation": explanation}, upload_id, db)
        db.commit()
        return OSIStackReport(upload_id=upload_id, verdict="REVIEW", explanation=explanation, scan_duration_sec=scan_time, sha256_hash=sha256, steps=steps)
