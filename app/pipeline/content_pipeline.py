"""Content ingestion pipeline orchestration.

This module coordinates the content ingestion sequence: load a
Markdown file from disk, parse it into a :class:`~app.models.script.Script`,
and return the result. It contains no file I/O logic of its own (that
lives in :mod:`app.utils.file_loader`) and no Markdown parsing logic
of its own (that lives in :mod:`app.services.markdown_parser`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.models.script import Script
from app.services.markdown_parser import parse_markdown
from app.utils.file_loader import load_markdown_file


@dataclass(frozen=True, slots=True)
class ContentIngestionResult:
    """Outcome of running the content ingestion pipeline.

    Attributes:
        script: The parsed :class:`~app.models.script.Script`.
        source_path: The path of the Markdown file that was ingested.
    """

    script: Script
    source_path: Path


def run_content_pipeline(markdown_path: Path) -> ContentIngestionResult:
    """Run the content ingestion pipeline for a single Markdown file.

    Sequence:
        1. Load the raw Markdown text from ``markdown_path``.
        2. Parse the raw text into a :class:`~app.models.script.Script`.
        3. Return a :class:`ContentIngestionResult`.

    Args:
        markdown_path: Path to the source Markdown file to ingest.

    Returns:
        A :class:`ContentIngestionResult` containing the parsed
        script and the originating file path.

    Raises:
        FileLoadError: If the Markdown file cannot be loaded from disk.
        MarkdownParsingError: If the Markdown content cannot be parsed
            into a valid :class:`~app.models.script.Script`.
    """
    raw_text = load_markdown_file(markdown_path)
    script = parse_markdown(raw_text)
    return ContentIngestionResult(script=script, source_path=markdown_path)
