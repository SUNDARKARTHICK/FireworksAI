"""Unit tests for the shared segment basename helper.

Scope is intentionally limited to
:func:`app.utils.segment_namer.build_segment_basename`. No filesystem
access occurs in this test file, matching the purity of the function.
"""

from __future__ import annotations

from app.utils.segment_namer import build_segment_basename


class TestBuildSegmentBasename:
    """Tests for :func:`build_segment_basename`."""

    def test_zero_index_produces_zero_padded_basename(self) -> None:
        """Index 0 produces '00_<label>'."""
        assert build_segment_basename(0, "introduction") == "00_introduction"

    def test_single_digit_index_is_zero_padded(self) -> None:
        """Indices below 10 are zero-padded to two digits."""
        assert build_segment_basename(3, "safety") == "03_safety"

    def test_double_digit_index_is_not_truncated(self) -> None:
        """Indices at or above 10 are represented in full."""
        assert build_segment_basename(12, "wrap-up") == "12_wrap-up"

    def test_index_above_99_expands_beyond_two_digits(self) -> None:
        """An index of 100 or more is not clipped to two digits."""
        assert build_segment_basename(100, "extra") == "100_extra"

    def test_no_extension_is_included(self) -> None:
        """The basename never includes a file extension or dot."""
        result = build_segment_basename(0, "introduction")

        assert "." not in result

    def test_sanitizes_uppercase_and_whitespace(self) -> None:
        """Uppercase letters and internal whitespace are sanitized."""
        result = build_segment_basename(2, "Mixed CASE Label")

        assert result == "02_mixed-case-label"

    def test_sanitizes_special_characters(self) -> None:
        """Punctuation/special characters are replaced with hyphens."""
        result = build_segment_basename(1, "mg$o4!!")

        assert result == "01_mg-o4"

    def test_empty_label_falls_back_to_generic_segment_name(self) -> None:
        """A label with no usable characters falls back to 'segment'."""
        result = build_segment_basename(5, "!!!---")

        assert result == "05_segment"

    def test_is_deterministic_for_the_same_input(self) -> None:
        """Calling the function twice with the same input is stable."""
        first = build_segment_basename(1, "history")
        second = build_segment_basename(1, "history")

        assert first == second

    def test_basename_contains_no_path_separators(self) -> None:
        """The generated basename never contains a path separator."""
        result = build_segment_basename(1, "a/b\\c")

        assert "/" not in result
        assert "\\" not in result
