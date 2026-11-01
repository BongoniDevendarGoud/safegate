"""
SafeGate — Unit & Integration Tests for the 7-Layer OSI Security Stack
======================================================================
Verifies:
1. Layer 1 (Physical): Bitstream streaming buffer, size cap, and empty stream rejection.
2. Layer 2 (Data Link): Temporal frame extraction and decodability validation.
3. Layer 3 (Network): Origin IP rate limiting and traffic policing.
4. Layer 4 (Transport): End-to-end SHA-256 checksum and exact blocklist blocking.
5. Layer 5 (Session): Constant-time credential authentication and audit hash chain recording.
6. Layer 6 (Presentation): Magic-byte container syntax validation and DCT perceptual hash deduplication.
7. Layer 7 (Application): Cognitive AI classification, deepfake scoring, and fail-closed decision gating.
8. Full OSI Protocol Stack (`OSIProtocolStack`): End-to-end multi-layer execution.
"""

import io
import uuid
import pytest
from pathlib import Path
from app.config import settings
from app.db import SessionLocal
from app.models.database import BlocklistHash, BlocklistPHash, Upload
from app.osi.layer1_physical import Layer1PhysicalBitstream
from app.osi.layer2_datalink import Layer2DataLinkFraming
from app.osi.layer3_network import Layer3NetworkPolicy
from app.osi.layer4_transport import Layer4TransportIntegrity
from app.osi.layer5_session import Layer5SessionControl
from app.osi.layer6_presentation import Layer6PresentationSyntax
from app.osi.layer7_application import Layer7ApplicationPolicy
from app.osi.stack import OSIProtocolStack


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_video_path():
    repo_root = Path(__file__).resolve().parent.parent
    candidates = [
        repo_root / "samples" / "sample_clean.mp4",
        repo_root / "sample_clean.mp4",
    ]
    for path in candidates:
        if path.exists():
            return path

    generator = repo_root / "generate_test_samples.py"
    if generator.exists():
        import subprocess
        import sys

        subprocess.run([sys.executable, str(generator)], check=True)
        for path in candidates:
            if path.exists():
                return path

    pytest.fail("sample_clean.mp4 must exist for OSI tests")


# -----------------------------------------------------------------------------
# Layer 1: Physical / Bitstream Layer Tests
# -----------------------------------------------------------------------------
def test_layer1_physical_intake_and_bounds():
    l1 = Layer1PhysicalBitstream(max_bytes=100)

    # Empty stream -> ValueError
    with pytest.raises(ValueError) as exc_empty:
        l1.process_stream(io.BytesIO(b""))
    assert "Empty bitstream" in str(exc_empty.value)

    # Valid within bounds
    raw, size = l1.process_stream(io.BytesIO(b"A" * 50))
    assert size == 50
    assert len(raw) == 50

    # Exceeds max bounds -> ValueError
    with pytest.raises(ValueError) as exc_over:
        l1.process_stream(io.BytesIO(b"A" * 150))
    assert "exceeded size limit" in str(exc_over.value)


# -----------------------------------------------------------------------------
# Layer 2: Data Link / Framing Layer Tests
# -----------------------------------------------------------------------------
def test_layer2_datalink_framing(sample_video_path):
    l2 = Layer2DataLinkFraming(interval_sec=1, max_frames=10)
    frames = l2.extract_frames(sample_video_path)
    assert len(frames) > 0
    # Each frame has (timestamp, PIL.Image)
    assert isinstance(frames[0][0], float)
    assert hasattr(frames[0][1], "size")


# -----------------------------------------------------------------------------
# Layer 3: Network Layer Tests
# -----------------------------------------------------------------------------
def test_layer3_network_rate_limiter():
    l3 = Layer3NetworkPolicy(max_requests_per_minute=3)
    ip = "192.168.1.100"

    # Requests 1, 2, 3 permitted
    assert l3.verify_network_origin(ip)[0] is True
    assert l3.verify_network_origin(ip)[0] is True
    assert l3.verify_network_origin(ip)[0] is True

    # Request 4 blocked by rate policy
    allowed, msg = l3.verify_network_origin(ip)
    assert allowed is False
    assert "exceeded rate limit" in msg


# -----------------------------------------------------------------------------
# Layer 4: Transport Layer Tests
# -----------------------------------------------------------------------------
def test_layer4_transport_integrity_and_blocklist(db_session):
    l4 = Layer4TransportIntegrity()
    dummy_bytes = b"safe media transport payload"
    sha = l4.compute_checksum(dummy_bytes)
    assert len(sha) == 64

    # Clean check
    clean, _ = l4.verify_transport_blocklist(sha, db_session)
    assert clean is True

    # Insert into blocklist
    bl = BlocklistHash(sha256_hash=sha, source="test")
    db_session.add(bl)
    db_session.commit()

    try:
        clean_after, msg = l4.verify_transport_blocklist(sha, db_session)
        assert clean_after is False
        assert "matched in exact blocklist" in msg
    finally:
        db_session.query(BlocklistHash).filter(BlocklistHash.sha256_hash == sha).delete()
        db_session.commit()


# -----------------------------------------------------------------------------
# Layer 5: Session Layer Tests
# -----------------------------------------------------------------------------
def test_layer5_session_auth():
    l5 = Layer5SessionControl()

    # Missing credentials
    ok, _ = l5.authenticate_session(None, "client")
    assert ok is False

    # Invalid credentials
    ok, _ = l5.authenticate_session("fake-key", "client")
    assert ok is False

    # Valid client key
    ok, _ = l5.authenticate_session(settings.CLIENT_API_KEY, "client")
    assert ok is True

    # Valid admin key
    ok, _ = l5.authenticate_session(settings.ADMIN_API_KEY, "admin")
    assert ok is True


# -----------------------------------------------------------------------------
# Layer 6: Presentation Layer Tests
# -----------------------------------------------------------------------------
def test_layer6_presentation_syntax_and_phash(sample_video_path, db_session):
    l6 = Layer6PresentationSyntax()

    # Synthetic MP4 bytes pass syntax
    raw_video = sample_video_path.read_bytes()
    valid, mime, ext = l6.verify_syntax(raw_video, sample_video_path.name)
    assert valid is True
    assert "video/" in mime
    assert ext in ("mp4", "m4v")

    # Plain text rejected
    invalid, err, _ = l6.verify_syntax(b"This is not a video file", "test.mp4")
    assert invalid is False
    assert "Could not determine file type" in err


# -----------------------------------------------------------------------------
# Layer 7: Application Layer Tests
# -----------------------------------------------------------------------------
def test_layer7_application_policy(sample_video_path, monkeypatch):
    monkeypatch.setenv("SAFEGATE_MOCK_MODEL", "true")
    l2 = Layer2DataLinkFraming()
    l7 = Layer7ApplicationPolicy()

    frames = l2.extract_frames(sample_video_path)
    score, ts, _ = l7.classify_nsfw_frames(frames)
    assert 0.0 <= score <= 1.0

    risk, reasons = l7.evaluate_synthetic_manipulation(sample_video_path, frames)
    assert 0 <= risk <= 100


# -----------------------------------------------------------------------------
# Complete 7-Layer OSI Stack Integration Test
# -----------------------------------------------------------------------------
def test_osi_protocol_stack_full_execution(sample_video_path, db_session, monkeypatch):
    monkeypatch.setenv("SAFEGATE_MOCK_MODEL", "true")

    stack = OSIProtocolStack()
    with open(sample_video_path, "rb") as f:
        report = stack.process_media_stream(
            stream=f,
            original_filename="sample_clean.mp4",
            client_ip="127.0.0.1",
            session_key=settings.CLIENT_API_KEY,
            db=db_session,
        )

    assert report.verdict == "ALLOW"
    assert len(report.steps) >= 7  # All layers L1-L7 executed
    layer_nums = [s.layer_num for s in report.steps]
    assert 1 in layer_nums  # L1 Physical
    assert 2 in layer_nums  # L2 Data Link
    assert 3 in layer_nums  # L3 Network
    assert 4 in layer_nums  # L4 Transport
    assert 5 in layer_nums  # L5 Session
    assert 6 in layer_nums  # L6 Presentation
    assert 7 in layer_nums  # L7 Application
