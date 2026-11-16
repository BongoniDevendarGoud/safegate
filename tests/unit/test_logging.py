import json
import logging

from safegate_api.logging import (
    SafeGateJSONFormatter,
    correlation_id_ctx,
    redact_sensitive_text,
    tenant_id_ctx,
    upload_id_ctx,
)


def test_redact_sensitive_text() -> None:
    """Verify that sensitive tokens, emails, and credentials are redacted."""
    raw = "User user@example.com logged in with Bearer abcdef1234567890xyz and password=SuperSecretPassword123"
    redacted = redact_sensitive_text(raw)

    assert "[REDACTED_EMAIL]" in redacted
    assert "user@example.com" not in redacted
    assert "[REDACTED_TOKEN]" in redacted
    assert "abcdef1234567890xyz" not in redacted
    assert "SuperSecretPassword123" not in redacted


def test_safegate_json_formatter() -> None:
    """Verify structured JSON formatting including context vars and extra attributes."""
    corr_token = correlation_id_ctx.set("corr-test-123")
    tenant_token = tenant_id_ctx.set("tenant-test-456")
    upload_token = upload_id_ctx.set("upload-test-789")

    try:
        formatter = SafeGateJSONFormatter()
        logger = logging.getLogger("test_logger")
        record = logger.makeRecord(
            name="test_logger",
            level=logging.INFO,
            fn="test_logging.py",
            lno=42,
            msg="Processing upload payload for user@safegate.test",
            args=(),
            exc_info=None,
        )

        formatted_json = formatter.format(record)
        data = json.loads(formatted_json)

        assert data["level"] == "INFO"
        assert data["service"] == "safegate-api"
        assert data["correlation_id"] == "corr-test-123"
        assert data["tenant_id"] == "tenant-test-456"
        assert data["upload_id"] == "upload-test-789"
        assert "[REDACTED_EMAIL]" in data["message"]
        assert "user@safegate.test" not in data["message"]
        assert "timestamp" in data
    finally:
        correlation_id_ctx.reset(corr_token)
        tenant_id_ctx.reset(tenant_token)
        upload_id_ctx.reset(upload_token)
