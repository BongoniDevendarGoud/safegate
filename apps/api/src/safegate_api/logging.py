"""
SafeGate Structured Logging Subsystem.
Implements high-throughput, contextual JSON logging with sensitive token redaction.
"""

from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any

# Context variable tracking current request/upload correlation trace
correlation_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)
tenant_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "tenant_id", default=None
)
upload_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "upload_id", default=None
)

# Patterns for sensitive credentials to scrub from logs
REDACTION_PATTERNS = [
    (re.compile(r"(bearer\s+)[A-Za-z0-9_\-\.]{15,}", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
    (
        re.compile(
            r'((?:"?)(?:password|secret|api_key|token|access_key)(?:"?)\s*[:=]\s*(?:"?))([^",\s]+)((?:"?))',
            re.IGNORECASE,
        ),
        r"\1[REDACTED]\3",
    ),
    (
        re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", re.IGNORECASE),
        r"[REDACTED_EMAIL]",
    ),
]


def redact_sensitive_text(text: str) -> str:
    """Scrubs sensitive tokens, passwords, and PII from log messages."""
    for pattern, replacement in REDACTION_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class SafeGateJSONFormatter(logging.Formatter):
    """
    Formats log records into structured JSON with timestamps, levels,
    correlation tracing, and redaction.
    """

    def format(self, record: logging.LogRecord) -> str:
        raw_msg = record.getMessage()
        clean_msg = redact_sensitive_text(raw_msg)

        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": clean_msg,
            "service": "safegate-api",
            "correlation_id": correlation_id_ctx.get(),
            "tenant_id": tenant_id_ctx.get(),
            "upload_id": upload_id_ctx.get(),
            "source": f"{record.filename}:{record.lineno}",
        }

        # Include structured extra attributes if provided
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            payload.update(record.extra_fields)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload)


def setup_logging(level: str = "INFO", json_output: bool = True) -> logging.Logger:
    """
    Initializes root and SafeGate loggers.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    if json_output:
        stream_handler.setFormatter(SafeGateJSONFormatter())
    else:
        stream_handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")
        )

    root_logger.addHandler(stream_handler)

    # Suppress verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = logging.getLogger("safegate")
    return logger


logger = setup_logging()
