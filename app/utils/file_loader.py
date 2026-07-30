"""Safe file loading utility for Markdown source files.

This module is responsible only for safely reading a file from disk
and returning its raw text content. It has no knowledge of Markdown
syntax, YAML front matter, or the :class:`~app.models.script.Script`
model — that responsibility belongs to
:mod:`app.services.markdown_parser`.
"""

from __future__ import annotations

from pathlib import Path

from app.exceptions import FileLoadError


def load_markdown_file(path: Path) -> str:
    """Load a Markdown file from disk and return its raw text content.

    Args:
        path: Path to the Markdown file to load.

    Returns:
        The raw, unparsed text content of the file.

    Raises:
        FileLoadError: If the path does not exist, is not a regular
            file, or cannot be read (e.g. due to permissions or
            encoding errors).
    """
    if not path.exists():
        raise FileLoadError(f"Markdown file not found: {path}")

    if not path.is_file():
        raise FileLoadError(f"Path is not a regular file: {path}")

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise FileLoadError(
            f"Markdown file '{path}' is not valid UTF-8 text: {exc}"
        ) from exc
    except OSError as exc:
        raise FileLoadError(f"Failed to read Markdown file '{path}': {exc}") from exc
