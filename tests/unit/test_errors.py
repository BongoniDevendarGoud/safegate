from safegate_api.errors import (
    ChildSafetyEscalationError,
    ErrorCode,
    FailClosedTriggeredError,
    MediaDecodeError,
    ModelInferenceError,
    ProblemDetails,
    QuarantineViolationError,
    TamperDetectedError,
)


def test_problem_details_serialization() -> None:
    """Verify ProblemDetails schema complies with RFC 7807."""
    problem = ProblemDetails(
        type="https://safegate.ai/errors/invalid_input",
        title="Invalid Input",
        status=400,
        detail="Payload validation failed on parameter 'format'",
        instance="/v1/media/upload/test-1",
        code=ErrorCode.INVALID_INPUT,
        correlation_id="corr-999",
        invalid_params={"format": "Must be one of ['mp4', 'mov', 'jpg', 'png']"},
    )

    data = problem.model_dump()
    assert data["status"] == 400
    assert data["code"] == "INVALID_INPUT"
    assert data["correlation_id"] == "corr-999"
    assert "format" in data["invalid_params"]


def test_safegate_exception_conversion() -> None:
    """Verify SafeGateException converts correctly to ProblemDetails."""
    exc = MediaDecodeError(
        detail="Atom 'moov' not found before EOF",
    )

    assert exc.status_code == 422
    assert exc.code == ErrorCode.DECODE_ERROR

    problem = exc.to_problem_details(
        instance="/v1/media/stream/abc-123",
        correlation_id="corr-test-decode",
    )

    assert problem.status == 422
    assert problem.code == ErrorCode.DECODE_ERROR
    assert problem.detail == "Atom 'moov' not found before EOF"
    assert problem.correlation_id == "corr-test-decode"


def test_fail_closed_exception() -> None:
    """Verify FailClosedTriggeredError enforces 503 status and fail-closed code."""
    exc = FailClosedTriggeredError(
        component="detector_pool",
        reason="Worker pool exhausted; fail-closed policy routed upload to review",
    )

    assert exc.status_code == 503
    assert exc.code == ErrorCode.FAIL_CLOSED_TRIGGERED


def test_child_safety_escalation_exception() -> None:
    """Verify ChildSafetyEscalationError triggers restricted 451 legal escalation."""
    exc = ChildSafetyEscalationError(
        identifier="upload-csam-mock-001",
        reason="Statutory perceptual hash match against restricted ledger",
    )

    assert exc.status_code == 451
    assert exc.code == ErrorCode.RESTRICTED_ESCALATION


def test_additional_exception_codes() -> None:
    """Verify QuarantineViolationError, ModelInferenceError, and TamperDetectedError."""
    quarantine_exc = QuarantineViolationError(asset_id="asset-999")
    assert quarantine_exc.status_code == 403
    assert quarantine_exc.code == ErrorCode.QUARANTINE_VIOLATION

    model_exc = ModelInferenceError(model_name="spatial_effnet", reason="CUDA OOM")
    assert model_exc.status_code == 502
    assert model_exc.code == ErrorCode.MODEL_INFERENCE_FAILURE

    tamper_exc = TamperDetectedError(ledger_entry_id="ledger-0042")
    assert tamper_exc.status_code == 500
    assert tamper_exc.code == ErrorCode.TAMPER_DETECTED
