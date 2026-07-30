"""Markdown parsing service for lesson scripts.

This module parses raw Markdown text (already loaded into memory) into
a validated :class:`~app.models.script.Script` object. It performs no
file I/O of any kind — reading files from disk is the responsibility
of :mod:`app.utils.file_loader`.

Expected Markdown structure::

    ---
    title: ...
    author: ...
    date: ...
    language: en
    voice: ...
    tags: [tag-one, tag-two]
    ---

    ## Introduction
    ...

    ## Section Title
    ...

    ## Conclusion
    ...
"""

from __future__ import annotations

import re
from typing import Any

import yaml

from app.exceptions import MarkdownParsingError
from app.models.script import Metadata, Script, Section

_FRONT_MATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_HEADING_PATTERN = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
_REQUIRED_METADATA_FIELDS = ("title", "author", "date")


def parse_markdown(raw_text: str) -> Script:
    """Parse raw Markdown text into a :class:`Script`.

    Args:
        raw_text: The full raw Markdown document, including YAML
            front matter.

    Returns:
        A validated :class:`~app.models.script.Script` instance
        containing metadata, introduction, sections, and conclusion.

    Raises:
        MarkdownParsingError: If front matter is missing or invalid,
            required metadata fields are missing, or the document
            does not contain an introduction, at least one content
            section, and a conclusion in the expected order.
    """
    front_matter_raw, body = _split_front_matter(raw_text)
    metadata = _parse_metadata(front_matter_raw)
    introduction, sections, conclusion = _parse_body(body)

    return Script(
        metadata=metadata,
        introduction=introduction,
        sections=sections,
        conclusion=conclusion,
    )


def _split_front_matter(raw_text: str) -> tuple[str, str]:
    """Split raw Markdown into its YAML front matter and body.

    Args:
        raw_text: The full raw Markdown document.

    Returns:
        A tuple of ``(front_matter_yaml, body_markdown)``.

    Raises:
        MarkdownParsingError: If the document does not start with a
            valid ``---`` delimited front matter block.
    """
    match = _FRONT_MATTER_PATTERN.match(raw_text)
    if not match:
        raise MarkdownParsingError(
            "Markdown document is missing required YAML front matter "
            "delimited by '---' lines."
        )
    return match.group(1), raw_text[match.end() :]


def _parse_metadata(front_matter_raw: str) -> Metadata:
    """Parse and validate YAML front matter into a :class:`Metadata`.

    Args:
        front_matter_raw: The raw YAML text between the front matter
            delimiters.

    Returns:
        A validated :class:`~app.models.script.Metadata` instance.

    Raises:
        MarkdownParsingError: If the YAML is invalid, is not a mapping,
            or is missing required fields.
    """
    try:
        data: Any = yaml.safe_load(front_matter_raw)
    except yaml.YAMLError as exc:
        raise MarkdownParsingError(f"Invalid YAML front matter: {exc}") from exc

    if not isinstance(data, dict):
        raise MarkdownParsingError(
            "YAML front matter must define a mapping of metadata fields."
        )

    missing = [field for field in _REQUIRED_METADATA_FIELDS if not data.get(field)]
    if missing:
        raise MarkdownParsingError(
            f"Missing required metadata field(s): {', '.join(missing)}"
        )

    raw_tags = data.get("tags", ())
    if isinstance(raw_tags, (list, tuple)):
        tags = tuple(str(tag) for tag in raw_tags)
    else:
        raise MarkdownParsingError("Metadata field 'tags' must be a list.")

    return Metadata(
        title=str(data["title"]),
        author=str(data["author"]),
        date=str(data["date"]),
        language=str(data.get("language", "en")),
        voice=str(data["voice"]) if data.get("voice") is not None else None,
        tags=tags,
    )


def _parse_body(body: str) -> tuple[str, tuple[Section, ...], str]:
    """Parse the Markdown body into introduction, sections, and conclusion.

    Args:
        body: The Markdown body text following the front matter,
            expected to contain ``## `` level headings marking the
            introduction, one or more content sections, and the
            conclusion, in that order.

    Returns:
        A tuple of ``(introduction, sections, conclusion)``.

    Raises:
        MarkdownParsingError: If fewer than three headings are found,
            or the first/last headings are not named "Introduction"
            and "Conclusion" respectively (case-insensitive).
    """
    headings = list(_HEADING_PATTERN.finditer(body))

    if len(headings) < 3:
        raise MarkdownParsingError(
            "Markdown body must contain an 'Introduction' heading, at "
            "least one content section heading, and a 'Conclusion' "
            "heading."
        )

    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(headings):
        heading_title = match.group(1).strip()
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        content = body[start:end].strip()
        blocks.append((heading_title, content))

    if blocks[0][0].lower() != "introduction":
        raise MarkdownParsingError(
            f"Expected the first heading to be 'Introduction', got '{blocks[0][0]}'."
        )
    if blocks[-1][0].lower() != "conclusion":
        raise MarkdownParsingError(
            f"Expected the last heading to be 'Conclusion', got '{blocks[-1][0]}'."
        )

    introduction = blocks[0][1]
    conclusion = blocks[-1][1]
    section_blocks = blocks[1:-1]

    if not section_blocks:
        raise MarkdownParsingError(
            "Markdown body must contain at least one content section "
            "between the 'Introduction' and 'Conclusion' headings."
        )

    sections = tuple(
        Section(heading=heading, content=content)
        for heading, content in section_blocks
    )

    return introduction, sections, conclusion
