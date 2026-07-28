"""Logging configuration helpers for FireworksAI.

This module provides a consistent logging setup that can be reused by all
application components and tests.
"""

from __future__ import annotations

import logging
from typing import Final

DEFAULT_LOG_FORMAT: Final[str] = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Configure and return the application logger.

    The logger is configured once per process and reuses the existing handlers
    to avoid duplicate output when the setup function is called repeatedly.
    """

    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO), format=DEFAULT_LOG_FORMAT)
    logger = logging.getLogger("fireworksai")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    return logger
