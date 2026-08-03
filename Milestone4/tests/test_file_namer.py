"""Unit tests for the file namer utility (Component 5).

Scope is intentionally limited to
:func:`app.utils.file_namer.build_filename`. No filesystem access
occurs in this test file, matching the purity of the function itself.
"""

from __future__ import annotations

from app.models.audio import NarrationSegment
from app.utils.file_namer import build_filename


class TestBuildFilename:
    """Tests for :func:`build_filename`."""

    def test_introduction_filename_matches_expected_format(self) -> None:
        """An introduction segment produces '00_introduction.mp3'."""
        segment = NarrationSegment(index=0, label="introduction", text="Hello.")

        filename = build_filename(segment)

        assert filename == "00_introduction.mp3"

    def test_section_filename_with_slug_label(self) -> None:
        """A section segment with a hyphenated label produces the expected name."""
        segment = NarrationSegment(
            index=1, label="history-of-fireworks", text="Some history."
        )

        filename = build_filename(segment)

        assert filename == "01_history-of-fireworks.mp3"

    def test_conclusion_filename_matches_expected_format(self) -> None:
        """A conclusion segment produces a filename like '04_conclusion.mp3'."""
        segment = NarrationSegment(index=4, label="conclusion", text="The end.")

        filename = build_filename(segment)

        assert filename == "04_conclusion.mp3"

    def test_single_digit_index_is_zero_padded(self) -> None:
        """Indices below 10 are zero-padded to two digits."""
        segment = NarrationSegment(index=3, label="safety", text="Be safe.")

        filename = build_filename(segment)

        assert filename.startswith("03_")

    def test_double_digit_index_is_not_truncated(self) -> None:
        """Indices at or above 10 are represented in full."""
        segment = NarrationSegment(index=12, label="wrap-up", text="Done.")

        filename = build_filename(segment)

        assert filename.startswith("12_")

    def test_index_above_99_expands_beyond_two_digits(self) -> None:
        """An index of 100 or more is not clipped to two digits."""
        segment = NarrationSegment(index=100, label="extra", text="More.")

        filename = build_filename(segment)

        assert filename.startswith("100_")

    def test_custom_extension_without_leading_dot(self) -> None:
        """A custom extension without a leading dot is applied correctly."""
        segment = NarrationSegment(index=0, label="introduction", text="Hi.")

        filename = build_filename(segment, extension="wav")

        assert filename == "00_introduction.wav"

    def test_custom_extension_with_leading_dot_is_normalized(self) -> None:
        """A custom extension with a leading dot is normalized (no double dot)."""
        segment = NarrationSegment(index=0, label="introduction", text="Hi.")

        filename = build_filename(segment, extension=".wav")

        assert filename == "00_introduction.wav"

    def test_sanitizes_uppercase_and_whitespace_in_label(self) -> None:
        """Uppercase letters and internal whitespace in a label are sanitized."""
        segment = NarrationSegment(index=2, label="Mixed CASE Label", text="X.")

        filename = build_filename(segment)

        assert filename == "02_mixed-case-label.mp3"

    def test_sanitizes_special_characters_in_label(self) -> None:
        """Punctuation/special characters in a label are replaced with hyphens."""
        segment = NarrationSegment(index=1, label="mg$o4!!", text="X.")

        filename = build_filename(segment)

        assert filename == "01_mg-o4.mp3"

    def test_empty_label_falls_back_to_generic_segment_name(self) -> None:
        """A label with no usable characters falls back to 'segment'."""
        segment = NarrationSegment(index=5, label="!!!---", text="X.")

        filename = build_filename(segment)

        assert filename == "05_segment.mp3"

    def test_is_deterministic_for_the_same_input(self) -> None:
        """Calling build_filename twice with the same segment yields the same result."""
        segment = NarrationSegment(index=1, label="history", text="X.")

        first = build_filename(segment)
        second = build_filename(segment)

        assert first == second

    def test_filename_contains_no_path_separators(self) -> None:
        """The generated filename never contains a path separator."""
        segment = NarrationSegment(index=1, label="a/b\\c", text="X.")

        filename = build_filename(segment)

        assert "/" not in filename
        assert "\\" not in filename
