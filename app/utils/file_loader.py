"""Utility for loading raw text content from Markdown files on disk.

This module is responsible only for file access. It does not parse or
interpret Markdown in any way — it returns the raw file contents as a
string, or raises a meaningful exception if that is not possible.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FileLoaderError(Exception):
    """Raised when a Markdown file cannot be located or read."""


def load_markdown_file(file_path: Path) -> str:
    """Read the full UTF-8 text content of a Markdown file.

    Args:
        file_path: Path to the Markdown file to read.

    Returns:
        The complete contents of the file as a string.

    Raises:
        FileLoaderError: If the file does not exist, is not a regular
            file, or cannot be read/decoded.
    """
    if not file_path.exists():
        logger.error("Markdown file not found: %s", file_path)
        raise FileLoaderError(f"File not found: {file_path}")

    if not file_path.is_file():
        logger.error("Path exists but is not a file: %s", file_path)
        raise FileLoaderError(f"Path is not a file: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        logger.error("Failed to decode file as UTF-8: %s", file_path)
        raise FileLoaderError(
            f"File is not valid UTF-8: {file_path}"
        ) from exc
    except OSError as exc:
        logger.error("OS error while reading file: %s", file_path)
        raise FileLoaderError(f"Could not read file: {file_path}") from exc

    logger.info("Loaded Markdown file: %s", file_path)
    return content
