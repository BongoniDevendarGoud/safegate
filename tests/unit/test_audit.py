from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from safegate_api.audit import record_audit_event, verify_ledger_integrity
from safegate_api.database import Base
from safegate_api.errors import TamperDetectedError
from safegate_api.models import AuditLedgerEntry


@pytest_asyncio.fixture
async def async_session(tmp_path: Path) -> AsyncGenerator[AsyncSession, None]:
    """Provides an isolated temporary SQLite database session for audit testing."""
    db_file = tmp_path / "test_audit.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_audit_ledger_chain_and_verify(async_session: AsyncSession) -> None:
    """Verify that multiple events form a valid cryptographic HMAC chain."""
    secret = "test_super_secret_audit_key_32_bytes"

    # 1. Record first event
    e1 = await record_audit_event(
        session=async_session,
        event_type="MEDIA_INGESTED",
        tenant_id="tenant-alpha",
        payload={"filename": "test1.mp4", "sha256": "abc123def456"},
        upload_id="upload-001",
        secret_key=secret,
    )
    assert e1.sequence_num == 1
    assert e1.prev_signature == "0" * 64

    # 2. Record second event
    e2 = await record_audit_event(
        session=async_session,
        event_type="VERDICT_ISSUED",
        tenant_id="tenant-alpha",
        payload={"verdict": "ALLOW", "confidence": 0.99},
        upload_id="upload-001",
        secret_key=secret,
    )
    assert e2.sequence_num == 2
    assert e2.prev_signature == e1.signature

    # 3. Verify integrity
    result = await verify_ledger_integrity(session=async_session, secret_key=secret)
    assert result.is_valid is True
    assert result.total_records == 2
    assert result.last_sequence == 2
    assert result.last_signature == e2.signature


@pytest.mark.asyncio
async def test_audit_ledger_detects_payload_tampering(async_session: AsyncSession) -> None:
    """Verify that modifying a historical payload breaks the hash chain."""
    secret = "test_super_secret_audit_key_32_bytes"

    await record_audit_event(
        session=async_session,
        event_type="MEDIA_INGESTED",
        tenant_id="tenant-alpha",
        payload={"filename": "original.mp4"},
        upload_id="upload-001",
        secret_key=secret,
    )

    # Malicious actor tampers with payload directly in the database
    e1 = await async_session.get(AuditLedgerEntry, 1)
    assert e1 is not None
    e1.payload_json = '{"filename":"tampered_malicious.mp4"}'
    await async_session.commit()

    with pytest.raises(TamperDetectedError) as exc_info:
        await verify_ledger_integrity(session=async_session, secret_key=secret)

    assert (
        "altered" in str(exc_info.value.detail).lower()
        or "signature" in str(exc_info.value.detail).lower()
    )


@pytest.mark.asyncio
async def test_audit_ledger_detects_signature_tampering(async_session: AsyncSession) -> None:
    """Verify that altering a signature triggers TamperDetectedError."""
    secret = "test_super_secret_audit_key_32_bytes"

    await record_audit_event(
        session=async_session,
        event_type="MEDIA_INGESTED",
        tenant_id="tenant-alpha",
        payload={"filename": "original.mp4"},
        upload_id="upload-001",
        secret_key=secret,
    )

    e1 = await async_session.get(AuditLedgerEntry, 1)
    assert e1 is not None
    e1.signature = "f" * 64
    await async_session.commit()

    with pytest.raises(TamperDetectedError) as exc_info:
        await verify_ledger_integrity(session=async_session, secret_key=secret)

    assert "signature invalid" in str(exc_info.value.detail).lower()
