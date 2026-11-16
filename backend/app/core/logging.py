"""
Structured Logging Configuration Module
Provides structured JSON logging in production and formatted logs in development.
"""

import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects for CloudWatch / structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Include custom extra fields if present
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_entry.update(record.extra)

        return json.dumps(log_entry)


def setup_logging(app_env: str = "development", debug: bool = False) -> logging.Logger:
    """Configure root and application loggers."""
    log_level = logging.DEBUG if debug else logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to prevent duplicate lines
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if app_env in ("production", "staging"):
        handler.setFormatter(JSONFormatter())
    else:
        # Standard human-readable console format for development
        dev_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        handler.setFormatter(logging.Formatter(dev_format, datefmt="%Y-%m-%d %H:%M:%S"))

    root_logger.addHandler(handler)

    # Quiet overly chatty third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logger = logging.getLogger("uninova")
    logger.setLevel(log_level)
    return logger
