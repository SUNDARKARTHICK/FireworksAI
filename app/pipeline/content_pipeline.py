"""Pipeline that coordinates Markdown lesson ingestion.

This module contains no file-reading logic and no Markdown-parsing
logic of its own. It only sequences calls to the file loader and the
Markdown parser, and returns the resulting Script object.
"""

import logging
from pathlib import Path

from app.models.script import Script
from app.services.markdown_parser import parse_markdown
from app.utils.file_loader import load_markdown_file

logger = logging.getLogger(__name__)


def run_content_pipeline(file_path: Path) -> Script:
    """Ingest a Markdown lesson file and return a structured Script.

    Workflow:
        1. Read the raw Markdown file from disk.
        2. Parse the Markdown text into a Script object.
        3. Return the Script object.

    Args:
        file_path: Path to the Markdown lesson file to ingest.

    Returns:
        A fully populated Script instance.

    Raises:
        FileLoaderError: If the file cannot be located or read.
        MarkdownParserError: If the Markdown content is malformed.
    """
    logger.info("Starting content pipeline for: %s", file_path)
    raw_text = load_markdown_file(file_path)
    script = parse_markdown(raw_text)
    logger.info("Content pipeline finished for: %s", file_path)
    return script
