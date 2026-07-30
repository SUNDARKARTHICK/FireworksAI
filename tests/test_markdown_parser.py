"""Unit tests for Milestone 2: content ingestion.

These tests verify:
    * Safe Markdown file loading, including error handling.
    * YAML front matter metadata extraction.
    * Section (introduction/sections/conclusion) extraction.
    * Correct construction of the Script model.
    * Rejection of invalid or malformed Markdown.
    * End-to-end behavior of the content ingestion pipeline.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.exceptions import FileLoadError, MarkdownParsingError
from app.models.script import Metadata, Script, Section
from app.pipeline.content_pipeline import ContentIngestionResult, run_content_pipeline
from app.services.markdown_parser import parse_markdown
from app.utils.file_loader import load_markdown_file

PHASE01_PATH = Path(__file__).resolve().parent.parent / "content" / "phase01.md"

VALID_MARKDOWN = """---
title: "Sample Lesson"
author: "Test Author"
date: "2026-07-30"
language: "en"
voice: "en-US-GuyNeural"
tags: ["a", "b"]
---

## Introduction
This is the introduction.

## First Topic
Content of the first topic.

## Second Topic
Content of the second topic.

## Conclusion
This is the conclusion.
"""


class TestLoadMarkdownFile:
    """Tests for :func:`app.utils.file_loader.load_markdown_file`."""

    def test_loads_existing_file_as_raw_string(self, tmp_path: Path) -> None:
        """An existing Markdown file is loaded and returned as raw text."""
        file_path = tmp_path / "sample.md"
        file_path.write_text(VALID_MARKDOWN, encoding="utf-8")

        content = load_markdown_file(file_path)

        assert content == VALID_MARKDOWN

    def test_loads_real_phase01_fixture(self) -> None:
        """The real phase01.md content fixture loads successfully."""
        content = load_markdown_file(PHASE01_PATH)

        assert content.startswith("---")
        assert "## Introduction" in content
        assert "## Conclusion" in content

    def test_missing_file_raises_file_load_error(self, tmp_path: Path) -> None:
        """A non-existent file path raises FileLoadError."""
        missing_path = tmp_path / "does_not_exist.md"

        with pytest.raises(FileLoadError):
            load_markdown_file(missing_path)

    def test_directory_path_raises_file_load_error(self, tmp_path: Path) -> None:
        """Passing a directory instead of a file raises FileLoadError."""
        with pytest.raises(FileLoadError):
            load_markdown_file(tmp_path)


class TestParseMarkdownMetadata:
    """Tests for metadata extraction in :func:`parse_markdown`."""

    def test_extracts_metadata_fields(self) -> None:
        """All metadata fields are correctly extracted from front matter."""
        script = parse_markdown(VALID_MARKDOWN)

        assert isinstance(script.metadata, Metadata)
        assert script.metadata.title == "Sample Lesson"
        assert script.metadata.author == "Test Author"
        assert script.metadata.date == "2026-07-30"
        assert script.metadata.language == "en"
        assert script.metadata.voice == "en-US-GuyNeural"
        assert script.metadata.tags == ("a", "b")

    def test_applies_default_language_when_absent(self) -> None:
        """Language defaults to 'en' when not specified in front matter."""
        markdown = VALID_MARKDOWN.replace('language: "en"\n', "")

        script = parse_markdown(markdown)

        assert script.metadata.language == "en"

    def test_missing_required_field_raises_error(self) -> None:
        """Missing a required metadata field raises MarkdownParsingError."""
        markdown = VALID_MARKDOWN.replace('author: "Test Author"\n', "")

        with pytest.raises(MarkdownParsingError):
            parse_markdown(markdown)


class TestParseMarkdownSections:
    """Tests for section extraction in :func:`parse_markdown`."""

    def test_extracts_introduction_and_conclusion(self) -> None:
        """Introduction and conclusion text are correctly extracted."""
        script = parse_markdown(VALID_MARKDOWN)

        assert script.introduction == "This is the introduction."
        assert script.conclusion == "This is the conclusion."

    def test_extracts_sections_in_order(self) -> None:
        """Content sections are extracted as Section objects, in order."""
        script = parse_markdown(VALID_MARKDOWN)

        assert len(script.sections) == 2
        assert all(isinstance(section, Section) for section in script.sections)
        assert script.sections[0].heading == "First Topic"
        assert script.sections[0].content == "Content of the first topic."
        assert script.sections[1].heading == "Second Topic"
        assert script.sections[1].content == "Content of the second topic."

    def test_phase01_fixture_has_three_sections(self) -> None:
        """The phase01.md fixture parses into exactly three sections."""
        raw_text = load_markdown_file(PHASE01_PATH)

        script = parse_markdown(raw_text)

        assert len(script.sections) == 3


class TestScriptCreation:
    """Tests verifying a complete, well-formed Script is produced."""

    def test_returns_script_instance(self) -> None:
        """parse_markdown returns a fully populated Script instance."""
        script = parse_markdown(VALID_MARKDOWN)

        assert isinstance(script, Script)
        assert script.metadata.title == "Sample Lesson"
        assert script.introduction
        assert script.sections
        assert script.conclusion

    def test_script_is_immutable(self) -> None:
        """Script and its nested models are frozen dataclasses."""
        script = parse_markdown(VALID_MARKDOWN)

        with pytest.raises(AttributeError):
            script.introduction = "changed"  # type: ignore[misc]


class TestInvalidMarkdown:
    """Tests verifying invalid Markdown is rejected with clear errors."""

    def test_missing_front_matter_raises_error(self) -> None:
        """Markdown without YAML front matter raises MarkdownParsingError."""
        markdown = "## Introduction\nNo front matter here.\n\n## Conclusion\nEnd.\n"

        with pytest.raises(MarkdownParsingError):
            parse_markdown(markdown)

    def test_invalid_yaml_raises_error(self) -> None:
        """Malformed YAML in front matter raises MarkdownParsingError."""
        markdown = "---\ntitle: [unclosed\n---\n\n## Introduction\nA\n\n## Conclusion\nB\n"

        with pytest.raises(MarkdownParsingError):
            parse_markdown(markdown)

    def test_missing_introduction_heading_raises_error(self) -> None:
        """A document without an Introduction heading raises an error."""
        markdown = VALID_MARKDOWN.replace("## Introduction", "## Overview")

        with pytest.raises(MarkdownParsingError):
            parse_markdown(markdown)

    def test_missing_conclusion_heading_raises_error(self) -> None:
        """A document without a Conclusion heading raises an error."""
        markdown = VALID_MARKDOWN.replace("## Conclusion", "## Wrap Up")

        with pytest.raises(MarkdownParsingError):
            parse_markdown(markdown)

    def test_no_content_sections_raises_error(self) -> None:
        """A document with only Introduction and Conclusion headings fails."""
        markdown = (
            "---\ntitle: t\nauthor: a\ndate: d\n---\n\n"
            "## Introduction\nIntro text.\n\n## Conclusion\nEnd text.\n"
        )

        with pytest.raises(MarkdownParsingError):
            parse_markdown(markdown)

    def test_tags_not_a_list_raises_error(self) -> None:
        """A non-list 'tags' field raises MarkdownParsingError."""
        markdown = VALID_MARKDOWN.replace('tags: ["a", "b"]', "tags: not-a-list")

        with pytest.raises(MarkdownParsingError):
            parse_markdown(markdown)


class TestContentPipeline:
    """Tests for :func:`app.pipeline.content_pipeline.run_content_pipeline`."""

    def test_pipeline_returns_ingestion_result(self, tmp_path: Path) -> None:
        """The pipeline loads and parses a file, returning a valid result."""
        file_path = tmp_path / "lesson.md"
        file_path.write_text(VALID_MARKDOWN, encoding="utf-8")

        result = run_content_pipeline(file_path)

        assert isinstance(result, ContentIngestionResult)
        assert result.source_path == file_path
        assert isinstance(result.script, Script)
        assert result.script.metadata.title == "Sample Lesson"

    def test_pipeline_on_real_phase01_fixture(self) -> None:
        """The pipeline successfully ingests the real phase01.md fixture."""
        result = run_content_pipeline(PHASE01_PATH)

        assert result.script.metadata.title == "How Fireworks Get Their Colors"
        assert len(result.script.sections) == 3
        assert result.script.introduction
        assert result.script.conclusion

    def test_pipeline_propagates_file_load_error(self, tmp_path: Path) -> None:
        """A missing file causes the pipeline to raise FileLoadError."""
        missing_path = tmp_path / "missing.md"

        with pytest.raises(FileLoadError):
            run_content_pipeline(missing_path)

    def test_pipeline_propagates_markdown_parsing_error(self, tmp_path: Path) -> None:
        """Invalid Markdown content causes the pipeline to raise MarkdownParsingError."""
        file_path = tmp_path / "invalid.md"
        file_path.write_text("no front matter here", encoding="utf-8")

        with pytest.raises(MarkdownParsingError):
            run_content_pipeline(file_path)
