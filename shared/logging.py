"""Structured JSON Logging for Custodian AI Services.

Configures standard Python logging to emit single-line structured JSON logs
containing timestamp, service name, log level, message, and contextual metadata.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    def __init__(self, service_name: str = "custodian-service"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": time.time(),
            "service": self.service_name,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include custom extra fields if present
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_entry["context"] = record.extra

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_json_logging(service_name: str, log_level: str = "INFO") -> logging.Logger:
    """Configure the root logger with a JSON formatter for the given service."""
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplication
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter(service_name=service_name))
    logger.addHandler(handler)
    logger.propagate = False

    return logger
