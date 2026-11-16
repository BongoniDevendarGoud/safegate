"""
SafeGate Tamper-Evident HMAC-SHA256 Audit Ledger Subsystem.
Ensures non-repudiation and cryptographic chaining of every system event.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from safegate_api.config import settings
from safegate_api.errors import TamperDetectedError
from safegate_api.models import AuditLedgerEntry

GENESIS_SIGNATURE = "0" * 64


@dataclass(frozen=True)
class AuditVerificationResult:
    is_valid: bool
    total_records: int
    last_sequence: int
    last_signature: str
    verified_at: str


def compute_payload_hash(payload: dict[str, Any]) -> tuple[str, str]:
    """Generates canonical JSON string and its SHA-256 hex digest."""
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return canonical_json, payload_hash


def format_audit_timestamp(dt: datetime) -> str:
    """Normalizes datetime to canonical UTC ISO8601 with Z suffix across all DB backends."""
    dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def compute_entry_hmac(
    secret: str,
    prev_sig: str,
    sequence_num: int,
    iso_timestamp: str,
    event_type: str,
    tenant_id: str,
    payload_hash: str,
) -> str:
    """Calculates HMAC-SHA256 over chained event components."""
    data_to_sign = (
        f"{prev_sig}:{sequence_num}:{iso_timestamp}:{event_type}:{tenant_id}:{payload_hash}"
    )
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=data_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


async def record_audit_event(
    session: AsyncSession,
    event_type: str,
    tenant_id: str,
    payload: dict[str, Any],
    upload_id: str | None = None,
    secret_key: str | None = None,
) -> AuditLedgerEntry:
    """
    Appends a new cryptographically chained audit entry into the ledger.
    """
    secret = secret_key or settings.audit.hmac_secret

    # Find the latest sequence record
    stmt = select(AuditLedgerEntry).order_by(desc(AuditLedgerEntry.sequence_num)).limit(1)
    result = await session.execute(stmt)
    latest_entry = result.scalar_one_or_none()

    if latest_entry is None:
        sequence_num = 1
        prev_sig = GENESIS_SIGNATURE
    else:
        sequence_num = latest_entry.sequence_num + 1
        prev_sig = latest_entry.signature

    now = datetime.now(UTC)
    iso_ts = format_audit_timestamp(now)
    canonical_json, payload_hash = compute_payload_hash(payload)

    signature = compute_entry_hmac(
        secret=secret,
        prev_sig=prev_sig,
        sequence_num=sequence_num,
        iso_timestamp=iso_ts,
        event_type=event_type,
        tenant_id=tenant_id,
        payload_hash=payload_hash,
    )

    entry = AuditLedgerEntry(
        sequence_num=sequence_num,
        timestamp=now,
        event_type=event_type,
        tenant_id=tenant_id,
        upload_id=upload_id,
        payload_hash=payload_hash,
        payload_json=canonical_json,
        prev_signature=prev_sig,
        signature=signature,
    )

    session.add(entry)
    await session.flush()
    return entry


async def verify_ledger_integrity(
    session: AsyncSession,
    secret_key: str | None = None,
) -> AuditVerificationResult:
    """
    Validates complete hash chain from genesis to head.
    Throws TamperDetectedError immediately upon detecting signature or sequence divergence.
    """
    secret = secret_key or settings.audit.hmac_secret

    stmt = select(AuditLedgerEntry).order_by(AuditLedgerEntry.sequence_num.asc())
    result = await session.execute(stmt)
    entries = result.scalars().all()

    if not entries:
        return AuditVerificationResult(
            is_valid=True,
            total_records=0,
            last_sequence=0,
            last_signature=GENESIS_SIGNATURE,
            verified_at=datetime.now(UTC).isoformat(),
        )

    expected_prev_sig = GENESIS_SIGNATURE
    expected_seq = 1

    for entry in entries:
        # Check sequence continuity
        if entry.sequence_num != expected_seq:
            raise TamperDetectedError(
                ledger_entry_id=f"Sequence gap detected: expected {expected_seq}, found {entry.sequence_num}"
            )

        # Check hash chaining to previous entry
        if entry.prev_signature != expected_prev_sig:
            raise TamperDetectedError(
                ledger_entry_id=f"Prev-signature mismatch at sequence {entry.sequence_num}"
            )

        # Recompute payload hash from canonical JSON
        computed_payload_hash = hashlib.sha256(entry.payload_json.encode("utf-8")).hexdigest()
        if computed_payload_hash != entry.payload_hash:
            raise TamperDetectedError(
                ledger_entry_id=f"Payload hash altered at sequence {entry.sequence_num}"
            )

        # Recompute HMAC signature
        iso_ts = format_audit_timestamp(entry.timestamp)
        computed_sig = compute_entry_hmac(
            secret=secret,
            prev_sig=entry.prev_signature,
            sequence_num=entry.sequence_num,
            iso_timestamp=iso_ts,
            event_type=entry.event_type,
            tenant_id=entry.tenant_id,
            payload_hash=entry.payload_hash,
        )

        if not hmac.compare_digest(computed_sig, entry.signature):
            raise TamperDetectedError(
                ledger_entry_id=f"Cryptographic signature invalid at sequence {entry.sequence_num}"
            )

        expected_prev_sig = entry.signature
        expected_seq += 1

    last_entry = entries[-1]
    return AuditVerificationResult(
        is_valid=True,
        total_records=len(entries),
        last_sequence=last_entry.sequence_num,
        last_signature=last_entry.signature,
        verified_at=datetime.now(UTC).isoformat(),
    )
