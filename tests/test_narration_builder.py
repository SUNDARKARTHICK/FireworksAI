"""Unit tests for the narration builder service (Component 2).

Scope is intentionally limited to
:func:`app.services.narration_builder.build_narration_segments`.
Script fixtures are constructed directly against the Milestone 2
model — no file loading or Markdown parsing is exercised here.
"""

from __future__ import annotations

from app.models.audio import NarrationSegment
from app.models.script import Metadata, Script, Section
from app.services.narration_builder import build_narration_segments


def _make_script(section_headings: tuple[str, ...]) -> Script:
    """Build a minimal Script fixture with the given section headings."""
    return Script(
        metadata=Metadata(title="Test Lesson", author="Author", date="2026-07-30"),
        introduction="This is the introduction.",
        sections=tuple(
            Section(heading=heading, content=f"Content for {heading}.")
            for heading in section_headings
        ),
        conclusion="This is the conclusion.",
    )


class TestBuildNarrationSegments:
    """Tests for :func:`build_narration_segments`."""

    def test_returns_tuple_of_narration_segments(self) -> None:
        """The builder returns a tuple of NarrationSegment instances."""
        script = _make_script(("First Topic", "Second Topic"))

        segments = build_narration_segments(script)

        assert isinstance(segments, tuple)
        assert all(isinstance(segment, NarrationSegment) for segment in segments)

    def test_segment_count_matches_intro_sections_conclusion(self) -> None:
        """Segment count equals introduction + sections + conclusion."""
        script = _make_script(("First Topic", "Second Topic", "Third Topic"))

        segments = build_narration_segments(script)

        assert len(segments) == 1 + 3 + 1

    def test_introduction_is_first_segment(self) -> None:
        """The introduction is always segment index 0 with the correct label."""
        script = _make_script(("First Topic",))

        segments = build_narration_segments(script)

        assert segments[0].index == 0
        assert segments[0].label == "introduction"
        assert segments[0].text == "This is the introduction."

    def test_conclusion_is_last_segment(self) -> None:
        """The conclusion is always the final segment with the correct label."""
        script = _make_script(("First Topic", "Second Topic"))

        segments = build_narration_segments(script)

        assert segments[-1].index == 3
        assert segments[-1].label == "conclusion"
        assert segments[-1].text == "This is the conclusion."

    def test_section_indices_are_sequential(self) -> None:
        """Section segments are indexed sequentially between intro and conclusion."""
        script = _make_script(("Alpha", "Beta", "Gamma"))

        segments = build_narration_segments(script)

        indices = [segment.index for segment in segments]
        assert indices == [0, 1, 2, 3, 4]

    def test_section_labels_are_slugified_from_headings(self) -> None:
        """Section headings are converted into lowercase, hyphenated labels."""
        script = _make_script(("The Role of Metal Salts", "Why Blue Is Hard"))

        segments = build_narration_segments(script)

        assert segments[1].label == "the-role-of-metal-salts"
        assert segments[2].label == "why-blue-is-hard"

    def test_section_content_maps_to_segment_text(self) -> None:
        """Each section's content becomes the corresponding segment's text."""
        script = _make_script(("First Topic",))

        segments = build_narration_segments(script)

        assert segments[1].text == "Content for First Topic."

    def test_heading_with_punctuation_and_numbers_is_slugified_correctly(self) -> None:
        """Punctuation and numbers in headings are handled cleanly."""
        script = _make_script(("MgSO4: A Case Study (Part 1)",))

        segments = build_narration_segments(script)

        assert segments[1].label == "mgso4-a-case-study-part-1"

    def test_heading_with_no_alphanumeric_characters_falls_back_to_section_index(
        self,
    ) -> None:
        """A heading with only punctuation falls back to 'section-<n>'."""
        script = _make_script(("---", "!!!"))

        segments = build_narration_segments(script)

        assert segments[1].label == "section-1"
        assert segments[2].label == "section-2"

    def test_single_section_script_produces_three_segments(self) -> None:
        """A script with exactly one section produces three total segments."""
        script = _make_script(("Only Topic",))

        segments = build_narration_segments(script)

        assert len(segments) == 3
        assert [segment.label for segment in segments] == [
            "introduction",
            "only-topic",
            "conclusion",
        ]

    def test_labels_are_lowercase_and_contain_no_whitespace(self) -> None:
        """All generated labels are lowercase with no whitespace characters."""
        script = _make_script(("Mixed CASE Heading With Spaces",))

        segments = build_narration_segments(script)

        for segment in segments:
            assert segment.label == segment.label.lower()
            assert " " not in segment.label
