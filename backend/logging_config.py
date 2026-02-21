"""Structured JSON logging for Cloud Run.

Cloud Run auto-parses JSON lines on stdout into structured ``jsonPayload``
fields in Cloud Logging, enabling reliable log-based metrics and filters.

Usage::

    from backend.logging_config import configure_logging
    configure_logging()
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import datetime, timezone

# Fields that job/request code passes via ``extra={}`` on log calls.
_KNOWN_EXTRA_FIELDS = frozenset(
    {
        "job_id",
        "lecture_id",
        "job_type",
        "status",
        "error",
        "request_id",
        "mode",
        "method",
        "path",
        "status_code",
        "duration_ms",
    }
)

_LEVEL_TO_SEVERITY = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
    logging.CRITICAL: "CRITICAL",
}


class CloudRunJsonFormatter(logging.Formatter):
    """Emit one JSON object per log line for Cloud Run / Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "severity": _LEVEL_TO_SEVERITY.get(record.levelno, "DEFAULT"),
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
        }

        # Extract known extra fields attached by application code.
        for field in _KNOWN_EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        # Include stack trace for ERROR+ messages.
        if record.exc_info and record.levelno >= logging.ERROR:
            payload["stack_trace"] = "".join(
                traceback.format_exception(*record.exc_info)
            )

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Install the JSON formatter on the root logger.

    Safe to call multiple times — clears existing handlers first.
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Remove default handlers (Python's StreamHandler w/ plain-text format).
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CloudRunJsonFormatter())
    root.addHandler(handler)
