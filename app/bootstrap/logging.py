"""Logging configuration and utilities."""

import logging
import sys
from typing import Any

from app.bootstrap.settings import get_settings


class Formatter(logging.Formatter):
    """Custom log formatter with structured output."""

    def __init__(self) -> None:
        super().__init__()
        self._formats = {
            logging.DEBUG: "\033[36m%(asctime)s [DEBUG] %(name)s: %(message)s\033[0m",
            logging.INFO: "\033[32m%(asctime)s [INFO] %(name)s: %(message)s\033[0m",
            logging.WARNING: "\033[33m%(asctime)s [WARN] %(name)s: %(message)s\033[0m",
            logging.ERROR: "\033[31m%(asctime)s [ERROR] %(name)s: %(message)s\033[0m",
            logging.CRITICAL: "\033[35m%(asctime)s [CRITICAL] %(name)s: %(message)s\033[0m",
        }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with level-specific formatting."""
        fmt = self._formats.get(record.levelno, self._formats[logging.INFO])
        formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logging(*, debug: bool | None = None) -> None:
    """Configure application logging.

    Args:
        debug: Enable debug logging. If None, reads from settings.
    """
    if debug is None:
        settings = get_settings()
        debug = settings.app.debug

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(Formatter())
    root_logger.addHandler(console_handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding structured context to logs."""

    def __init__(self, logger: logging.Logger, **context: Any) -> None:
        self._logger = logger
        self._context = context
        self._old_factory = logging.getLogRecordFactory()

    def _record_factory(self, *args: Any, **kwargs: Any) -> logging.LogRecord:
        record = self._old_factory(*args, **kwargs)
        for key, value in self._context.items():
            setattr(record, key, value)
        return record

    def __enter__(self) -> "LogContext":
        logging.setLogRecordFactory(self._record_factory)
        return self

    def __exit__(self, *args: Any) -> None:
        logging.setLogRecordFactory(self._old_factory)
