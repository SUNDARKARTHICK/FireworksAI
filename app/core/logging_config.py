"""Logging configuration for the FireworksAI application.

This module is the single place responsible for configuring Python's
``logging`` module: console output, rotating file output, and log
formatting. Application code should never use ``print()``; it should
obtain a logger via ``logging.getLogger(__name__)`` after
:func:`configure_logging` has been called.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.settings import Settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 3
_LOGGER_NAME = "fireworksai"


def configure_logging(
    settings: Settings,
    log_file: Path | None = None,
) -> logging.Logger:
    """Configure and return the application's root logger.

    Sets up a console handler and a rotating file handler, both using
    the log level defined in ``settings.log_level``. Calling this
    function multiple times is safe: existing handlers on the target
    logger are cleared first to avoid duplicate log lines.

    Args:
        settings: Validated application settings, used to determine
            the log level and default log directory.
        log_file: Optional explicit path to the log file. Defaults to
            ``<settings.output_dir>/logs/fireworksai.log``.

    Returns:
        The configured :class:`logging.Logger` instance for the
        application.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(settings.log_level)
    logger.propagate = False

    # Clear existing handlers to keep this function idempotent.
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(settings.log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    resolved_log_file = log_file or (settings.output_dir / "logs" / "fireworksai.log")
    resolved_log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        filename=resolved_log_file,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(settings.log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
