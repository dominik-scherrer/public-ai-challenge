"""Metadata-only diagnostics with explicit telemetry opt-in."""

import json
import logging
import os
from datetime import UTC, datetime

from publicai.config import TelemetrySettings


class JsonFormatter(logging.Formatter):
    """Format internal event names without serializing exception payloads or locals."""

    def format(self, record: logging.LogRecord) -> str:
        """Return a credential-safe JSON log line."""
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name,
                "exception_type": getattr(record, "error_type", None),
            }
        )


def configure(settings: TelemetrySettings) -> None:
    """Enable stderr application logging and optional content-free AI spans.

    Standard OTEL_EXPORTER_OTLP_* environment settings can send spans to a
    local Aspire collector when telemetry is explicitly enabled.
    """
    os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("publicai")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    # Third-party request/exception logs can contain URLs, prompts, or credentials.
    for name in ("httpx", "httpx2", "httpcore", "httpcore2", "openai", "pydantic_ai"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    if settings.enabled:
        import logfire

        logfire.configure(
            service_name=settings.service_name,
            service_version="0.1.0",
            send_to_logfire=settings.send_to_logfire,
            console=False,
            inspect_arguments=False,
        )
        logfire.instrument_pydantic_ai(
            include_content=False,
            include_binary_content=False,
            include_model_request_parameters=False,
        )
