"""Service for converting raw Markdown lesson text into a Script object.

Expected Markdown convention:

    ---
    title: ...
    author: ...
    language: ...
    category: ...
    duration: ...
    tags: [tag1, tag2]
    ---

    ## Introduction
    <introduction text>

    ## Section: <Heading 1>
    <section content>

    ## Section: <Heading 2>
    <section content>

    ## Conclusion
    <conclusion text>

This module receives Markdown text as input. It never reads files
directly — file access is the responsibility of ``file_loader.py``.
"""

import logging
import re

import yaml

from app.models.script import Metadata, Script, Section

logger = logging.getLogger(__name__)

_REQUIRED_METADATA_FIELDS = (
    "title",
    "author",
    "language",
    "category",
    "duration",
)

_FRONT_MATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)
_SECTION_HEADING_PATTERN = re.compile(
    r"^##\s*Section:\s*(.+)$", re.IGNORECASE | re.MULTILINE
)


class MarkdownParserError(Exception):
    """Raised when Markdown content is malformed or fails validation."""


def parse_markdown(markdown_text: str) -> Script:
    """Convert raw Markdown lesson text into a structured Script object.

    Args:
        markdown_text: The full raw Markdown content of a lesson,
            including YAML front matter.

    Returns:
        A populated Script instance.

    Raises:
        MarkdownParserError: If the front matter is missing, required
            metadata fields are absent, or the body structure
            (introduction/sections/conclusion) cannot be parsed.
    """
    front_matter_raw, body = _split_front_matter(markdown_text)
    metadata = _parse_metadata(front_matter_raw)
    introduction = _extract_introduction(body)
    sections = _extract_sections(body)
    conclusion = _extract_conclusion(body)

    logger.info("Parsed Markdown into Script for '%s'", metadata.title)
    return Script(
        metadata=metadata,
        introduction=introduction,
        sections=sections,
        conclusion=conclusion,
    )


def _split_front_matter(markdown_text: str) -> tuple[str, str]:
    """Split Markdown text into raw front matter and body sections."""
    match = _FRONT_MATTER_PATTERN.match(markdown_text.strip() + "\n")
    if not match:
        logger.error("Markdown is missing YAML front matter")
        raise MarkdownParserError("Markdown is missing YAML front matter")
    return match.group(1), match.group(2)


def _parse_metadata(front_matter_raw: str) -> Metadata:
    """Parse and validate the YAML front matter into a Metadata object."""
    try:
        raw = yaml.safe_load(front_matter_raw) or {}
    except yaml.YAMLError as exc:
        logger.error("Failed to parse YAML front matter")
        raise MarkdownParserError("Invalid YAML front matter") from exc

    missing = [f for f in _REQUIRED_METADATA_FIELDS if not raw.get(f)]
    if missing:
        logger.error("Missing required metadata fields: %s", missing)
        raise MarkdownParserError(
            f"Missing required metadata fields: {', '.join(missing)}"
        )

    tags = raw.get("tags") or []
    if not isinstance(tags, list):
        tags = [tags]

    return Metadata(
        title=str(raw["title"]),
        author=str(raw["author"]),
        language=str(raw["language"]),
        category=str(raw["category"]),
        duration=str(raw["duration"]),
        tags=[str(tag) for tag in tags],
    )


def _extract_introduction(body: str) -> str:
    """Extract the introduction block from the Markdown body."""
    match = re.search(
        r"^##\s*Introduction\s*\n(.*?)(?=^##\s|\Z)",
        body,
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    if not match:
        logger.error("Markdown is missing an Introduction section")
        raise MarkdownParserError("Missing '## Introduction' section")
    return match.group(1).strip()


def _extract_sections(body: str) -> list[Section]:
    """Extract all '## Section: <Heading>' blocks from the body."""
    headings = list(_SECTION_HEADING_PATTERN.finditer(body))
    if not headings:
        logger.error("Markdown contains no '## Section:' entries")
        raise MarkdownParserError("No sections found in Markdown")

    sections: list[Section] = []
    for index, heading_match in enumerate(headings):
        start = heading_match.end()
        end = (
            headings[index + 1].start()
            if index + 1 < len(headings)
            else len(body)
        )
        content = body[start:end]
        # Trim trailing content that belongs to a following '## Conclusion'.
        conclusion_match = re.search(
            r"^##\s*Conclusion\s*$", content, re.IGNORECASE | re.MULTILINE
        )
        if conclusion_match:
            content = content[: conclusion_match.start()]

        sections.append(
            Section(
                heading=heading_match.group(1).strip(),
                content=content.strip(),
            )
        )
    return sections


def _extract_conclusion(body: str) -> str:
    """Extract the conclusion block from the Markdown body."""
    match = re.search(
        r"^##\s*Conclusion\s*\n(.*)",
        body,
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    if not match:
        logger.error("Markdown is missing a Conclusion section")
        raise MarkdownParserError("Missing '## Conclusion' section")
    return match.group(1).strip()
