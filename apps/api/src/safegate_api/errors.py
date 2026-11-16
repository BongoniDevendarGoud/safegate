"""
SafeGate Error and Exception Subsystem.
Implements RFC 7807 Problem Details compliant error responses and fail-closed exceptions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ErrorCode(StrEnum):
    INVALID_INPUT = "INVALID_INPUT"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    DECODE_ERROR = "DECODE_ERROR"
    QUARANTINE_VIOLATION = "QUARANTINE_VIOLATION"
    MODEL_INFERENCE_FAILURE = "MODEL_INFERENCE_FAILURE"
    DEPENDENCY_TIMEOUT = "DEPENDENCY_TIMEOUT"
    FAIL_CLOSED_TRIGGERED = "FAIL_CLOSED_TRIGGERED"
    TAMPER_DETECTED = "TAMPER_DETECTED"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    RESTRICTED_ESCALATION = "RESTRICTED_ESCALATION"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ProblemDetails(BaseModel):
    """
    RFC 7807 compliant error representation.
    https://datatracker.ietf.org/doc/html/rfc7807
    """

    type: str = Field(
        default="about:blank",
        description="A URI reference that identifies the problem type",
    )
    title: str = Field(description="A short, human-readable summary of the problem type")
    status: int = Field(description="The HTTP status code applicable to this occurrence")
    detail: str = Field(description="A human-readable explanation specific to this occurrence")
    instance: str | None = Field(
        default=None,
        description="A URI reference that identifies the specific occurrence of the problem",
    )
    code: ErrorCode = Field(description="SafeGate standardized machine-readable error code")
    correlation_id: str | None = Field(
        default=None,
        description="Tracing correlation ID for log analysis",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="UTC ISO 8601 timestamp when the error occurred",
    )
    invalid_params: dict[str, Any] | None = Field(
        default=None,
        description="Detailed parameter validation errors if applicable",
    )


class SafeGateException(Exception):
    """
    Base exception class for all SafeGate firewall errors.
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        detail: str | None = None,
        type_uri: str = "https://safegate.ai/errors",
        invalid_params: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.detail = detail or message
        self.type_uri = f"{type_uri}/{code.value.lower()}"
        self.invalid_params = invalid_params

    def to_problem_details(
        self,
        instance: str | None = None,
        correlation_id: str | None = None,
    ) -> ProblemDetails:
        return ProblemDetails(
            type=self.type_uri,
            title=self.code.value.replace("_", " ").title(),
            status=self.status_code,
            detail=self.detail,
            instance=instance,
            code=self.code,
            correlation_id=correlation_id,
            invalid_params=self.invalid_params,
        )


class MediaDecodeError(SafeGateException):
    """Raised when an uploaded file cannot be parsed or decoded safely."""

    def __init__(self, detail: str):
        super().__init__(
            message=f"Media decoding failed: {detail}",
            code=ErrorCode.DECODE_ERROR,
            status_code=422,
            detail=detail,
        )


class QuarantineViolationError(SafeGateException):
    """Raised when an unapproved asset is requested outside quarantine."""

    def __init__(self, asset_id: str):
        super().__init__(
            message=f"Security violation: asset '{asset_id}' is held in quarantine and cannot be published.",
            code=ErrorCode.QUARANTINE_VIOLATION,
            status_code=403,
            detail=f"Asset {asset_id} does not have an ALLOW verdict and is forbidden from public egress.",
        )


class ModelInferenceError(SafeGateException):
    """Raised when an ML inference worker or model encounters an error."""

    def __init__(self, model_name: str, reason: str):
        super().__init__(
            message=f"Inference error on model '{model_name}': {reason}",
            code=ErrorCode.MODEL_INFERENCE_FAILURE,
            status_code=502,
            detail=f"Model {model_name} failed: {reason}. Enforcing fail-closed policy.",
        )


class TamperDetectedError(SafeGateException):
    """Raised when the HMAC audit chain verification detects cryptographic tampering."""

    def __init__(self, ledger_entry_id: str):
        super().__init__(
            message=f"Cryptographic tamper detected on ledger entry: {ledger_entry_id}",
            code=ErrorCode.TAMPER_DETECTED,
            status_code=500,
            detail=f"Audit hash-chain integrity check failed at entry {ledger_entry_id}.",
        )


class FailClosedTriggeredError(SafeGateException):
    """Raised when pipeline enters fail-closed state to protect host app."""

    def __init__(self, component: str, reason: str):
        super().__init__(
            message=f"Fail-closed invariant triggered by {component}: {reason}",
            code=ErrorCode.FAIL_CLOSED_TRIGGERED,
            status_code=503,
            detail=f"Component {component} encountered fatal condition: {reason}. Verdict defaulted to HUMAN_REVIEW/BLOCK.",
        )


class ChildSafetyEscalationError(SafeGateException):
    """Raised when media triggers restricted child safety hash match or API flag."""

    def __init__(self, identifier: str, reason: str = "Statutory hash match"):
        super().__init__(
            message=f"Restricted child safety escalation for asset '{identifier}': {reason}",
            code=ErrorCode.RESTRICTED_ESCALATION,
            status_code=451,
            detail=f"Asset {identifier} triggered statutory isolation protocol: {reason}.",
        )
