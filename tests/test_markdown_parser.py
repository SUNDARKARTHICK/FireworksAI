"""Unit tests for the Markdown ingestion pipeline (Milestone 2)."""

from pathlib import Path

import pytest

from app.models.script import Script
from app.services.markdown_parser import MarkdownParserError, parse_markdown
from app.utils.file_loader import FileLoaderError, load_markdown_file

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_LESSON_PATH = PROJECT_ROOT / "content" / "phase01.md"

VALID_MARKDOWN = """---
title: Sample Lesson
author: Jane Doe
language: en
category: Testing
duration: 5 min
tags: [test, sample]
---

## Introduction
This is the introduction.

## Section: First Topic
This is the first section's content.

## Section: Second Topic
This is the second section's content.

## Conclusion
This is the conclusion.
"""

INVALID_MARKDOWN_NO_FRONT_MATTER = """
## Introduction
Missing front matter entirely.

## Conclusion
Nothing to see here.
"""

INVALID_MARKDOWN_MISSING_METADATA = """---
title: Incomplete Lesson
---

## Introduction
Intro text.

## Section: Only Section
Some content.

## Conclusion
The end.
"""


def test_file_loads_successfully() -> None:
    """The sample lesson file should load and return non-empty text."""
    content = load_markdown_file(SAMPLE_LESSON_PATH)
    assert isinstance(content, str)
    assert "title:" in content


def test_missing_file_raises_file_loader_error() -> None:
    """Loading a non-existent file should raise FileLoaderError."""
    missing_path = PROJECT_ROOT / "content" / "does_not_exist.md"
    with pytest.raises(FileLoaderError):
        load_markdown_file(missing_path)


def test_markdown_parses_successfully() -> None:
    """Valid Markdown should parse into a Script without raising."""
    script = parse_markdown(VALID_MARKDOWN)
    assert isinstance(script, Script)


def test_metadata_exists() -> None:
    """The parsed Script should contain correctly populated metadata."""
    script = parse_markdown(VALID_MARKDOWN)
    assert script.metadata.title == "Sample Lesson"
    assert script.metadata.author == "Jane Doe"
    assert script.metadata.language == "en"
    assert script.metadata.category == "Testing"
    assert script.metadata.duration == "5 min"
    assert script.metadata.tags == ["test", "sample"]


def test_sections_exist() -> None:
    """The parsed Script should contain the expected sections in order."""
    script = parse_markdown(VALID_MARKDOWN)
    assert len(script.sections) == 2
    assert script.sections[0].heading == "First Topic"
    assert script.sections[1].heading == "Second Topic"


def test_script_object_created_with_all_fields() -> None:
    """The Script object should have non-empty introduction/conclusion."""
    script = parse_markdown(VALID_MARKDOWN)
    assert script.introduction == "This is the introduction."
    assert script.conclusion == "This is the conclusion."


def test_invalid_markdown_missing_front_matter_raises() -> None:
    """Markdown with no front matter at all should raise an error."""
    with pytest.raises(MarkdownParserError):
        parse_markdown(INVALID_MARKDOWN_NO_FRONT_MATTER)


def test_invalid_markdown_missing_metadata_raises() -> None:
    """Markdown missing required metadata fields should raise an error."""
    with pytest.raises(MarkdownParserError):
        parse_markdown(INVALID_MARKDOWN_MISSING_METADATA)


def test_sample_lesson_end_to_end() -> None:
    """The real phase01.md sample lesson should parse correctly."""
    content = load_markdown_file(SAMPLE_LESSON_PATH)
    script = parse_markdown(content)
    assert script.metadata.title == "Introduction to Python Functions"
    assert len(script.sections) == 3
    assert script.introduction != ""
    assert script.conclusion != ""
