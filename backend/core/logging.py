"""Structured logging setup."""

import logging
import sys
from typing import Optional

from backend.core.config import get_settings


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Return a logger with timestamps and configurable level."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)

    log_level = (level or get_settings().log_level).upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    return logger
