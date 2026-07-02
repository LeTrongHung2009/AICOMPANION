"""
companion/utils/logger.py
=========================
Centralized logging setup for MyCompanion.
Outputs to both console and rotating file. Arch Linux compatible.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


# ANSI color codes for console output
class Colors:
    RESET = "\033[0m"
    DEBUG = "\033[36m"    # Cyan
    INFO = "\033[32m"     # Green
    WARNING = "\033[33m"  # Yellow
    ERROR = "\033[31m"    # Red
    CRITICAL = "\033[35m" # Magenta
    BOLD = "\033[1m"
    DIM = "\033[2m"


class ColorFormatter(logging.Formatter):
    """ANSI colored console formatter."""

    LEVEL_COLORS = {
        logging.DEBUG: Colors.DEBUG,
        logging.INFO: Colors.INFO,
        logging.WARNING: Colors.WARNING,
        logging.ERROR: Colors.ERROR,
        logging.CRITICAL: Colors.CRITICAL,
    }

    FORMAT = "{dim}[{time}]{reset} {color}{bold}{level:<8}{reset} {dim}{name}{reset} — {msg}"

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, Colors.RESET)
        log_time = self.formatTime(record, "%H:%M:%S")
        formatted = self.FORMAT.format(
            dim=Colors.DIM,
            time=log_time,
            reset=Colors.RESET,
            color=color,
            bold=Colors.BOLD,
            level=record.levelname,
            name=record.name.split(".")[-1],
            msg=record.getMessage(),
        )
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)
        return formatted


class PlainFormatter(logging.Formatter):
    """Plain text formatter for file logging."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    max_bytes: int = 5 * 1024 * 1024,  # 5MB
    backup_count: int = 3,
) -> None:
    """
    Configure the root logger with console + optional file handlers.

    Args:
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional path to rotating log file.
        max_bytes: Maximum log file size before rotation.
        backup_count: Number of backup log files to keep.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler with color
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColorFormatter())
    console_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)

    # File handler (rotating)
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(PlainFormatter())
        file_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(file_handler)

    # Suppress overly verbose third-party loggers
    for noisy in ["websockets", "asyncio", "httpx", "httpcore", "urllib3"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root_logger.debug("Logging system initialized.")


def get_logger(name: str) -> logging.Logger:
    """Get a named logger."""
    return logging.getLogger(f"mycompanion.{name}")
