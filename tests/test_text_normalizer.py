"""Unit tests for the text normalizer service (Component 3).

Scope is intentionally limited to
:func:`app.services.text_normalizer.normalize_text` and
:func:`app.services.text_normalizer.normalize_segment`.
"""

from __future__ import annotations

from app.models.audio import NarrationSegment
from app.services.text_normalizer import (
    DEFAULT_ACRONYM_LOOKUP,
    normalize_segment,
    normalize_text,
)


class TestAcronymExpansion:
    """Tests for acronym/brand-name expansion."""

    def test_expands_fireworksai(self) -> None:
        """FireworksAI is expanded to 'Fireworks AI'."""
        result = normalize_text("Welcome to FireworksAI.")

        assert result == "Welcome to Fireworks AI."

    def test_expands_mgso4(self) -> None:
        """MgSO4 is expanded to its full chemical name."""
        result = normalize_text("We used MgSO4 in the mixture.")

        assert result == "We used Magnesium Sulfate in the mixture."

    def test_expands_tts(self) -> None:
        """TTS is expanded to 'Text To Speech'."""
        result = normalize_text("Our TTS engine renders audio.")

        assert result == "Our Text To Speech engine renders audio."

    def test_does_not_expand_partial_word_match(self) -> None:
        """A longer word containing an acronym as a substring is untouched."""
        result = normalize_text("TTSExtended is a different word.")

        assert "Text To Speech" not in result
        assert "TTSExtended" in result

    def test_custom_lookup_overrides_default(self) -> None:
        """An injected custom lookup is used instead of the default table."""
        custom_lookup = {"AI": "Artificial Intelligence"}

        result = normalize_text("This is about AI.", acronym_lookup=custom_lookup)

        assert result == "This is about Artificial Intelligence."

    def test_default_lookup_is_used_when_none_provided(self) -> None:
        """The module-level default lookup applies when none is passed."""
        result = normalize_text("FireworksAI and MgSO4 and TTS.")

        for expansion in DEFAULT_ACRONYM_LOOKUP.values():
            assert expansion in result


class TestYearNormalization:
    """Tests for bare 4-digit year expansion."""

    def test_expands_2026(self) -> None:
        """2026 is expanded to 'Twenty Twenty Six'."""
        result = normalize_text("The show airs in 2026.")

        assert result == "The show airs in Twenty Twenty Six."

    def test_expands_year_with_teen_second_group(self) -> None:
        """A year with a teen second group (e.g. 2015) is spoken correctly."""
        result = normalize_text("Founded in 2015.")

        assert result == "Founded in Twenty Fifteen."

    def test_expands_year_ending_in_zero(self) -> None:
        """A year ending in 00 (e.g. 1900) uses the 'Hundred' form."""
        result = normalize_text("Back in 1900.")

        assert result == "Back in Nineteen Hundred."

    def test_expands_year_with_single_digit_second_group(self) -> None:
        """A year like 2005 uses the 'Oh <digit>' form."""
        result = normalize_text("Released in 2005.")

        assert result == "Released in Twenty Oh Five."

    def test_does_not_expand_number_embedded_in_word(self) -> None:
        """A 4-digit number embedded directly in an alphanumeric token is untouched."""
        result = normalize_text("Model MK2026X remains unchanged.")

        assert "MK2026X" in result

    def test_does_not_expand_non_year_numbers(self) -> None:
        """Numbers outside the configured year range are left untouched."""
        result = normalize_text("There are 3026 stars visible tonight.")

        assert "3026" in result


class TestPunctuationCleanup:
    """Tests for punctuation cleanup."""

    def test_collapses_repeated_exclamation_marks(self) -> None:
        """Repeated exclamation marks collapse to a single one."""
        result = normalize_text("Wow!!! That was amazing!!")

        assert result == "Wow! That was amazing!"

    def test_collapses_repeated_question_marks(self) -> None:
        """Repeated question marks collapse to a single one."""
        result = normalize_text("Really??")

        assert result == "Really?"

    def test_collapses_long_dot_runs_to_ellipsis(self) -> None:
        """Four or more consecutive periods collapse to a standard ellipsis."""
        result = normalize_text("Wait for it.......")

        assert result == "Wait for it..."

    def test_removes_space_before_punctuation(self) -> None:
        """Stray whitespace immediately before punctuation is removed."""
        result = normalize_text("This is odd , but true .")

        assert result == "This is odd, but true."


class TestWhitespaceCleanup:
    """Tests for whitespace cleanup."""

    def test_collapses_multiple_spaces(self) -> None:
        """Runs of multiple spaces collapse into a single space."""
        result = normalize_text("Too    many     spaces.")

        assert result == "Too many spaces."

    def test_strips_leading_and_trailing_whitespace(self) -> None:
        """Leading and trailing whitespace is removed."""
        result = normalize_text("   padded text   ")

        assert result == "padded text"

    def test_collapses_newlines_and_tabs(self) -> None:
        """Newlines and tabs are treated as whitespace and collapsed."""
        result = normalize_text("Line one\n\nLine two\t\ttabbed")

        assert result == "Line one Line two tabbed"


class TestIdempotency:
    """Tests verifying normalization is stable across repeated application."""

    def test_normalizing_twice_produces_same_result(self) -> None:
        """Applying normalize_text a second time changes nothing further."""
        raw = "FireworksAI  hosted  a show in 2026!!! MgSO4 was used.   "

        once = normalize_text(raw)
        twice = normalize_text(once)

        assert once == twice

    def test_already_clean_text_is_unchanged(self) -> None:
        """Text that is already normalized passes through unchanged."""
        clean = "Fireworks AI hosted a show in Twenty Twenty Six."

        result = normalize_text(clean)

        assert result == clean


class TestEdgeCases:
    """Tests for edge-case inputs."""

    def test_empty_string_returns_empty_string(self) -> None:
        """An empty input string normalizes to an empty string."""
        result = normalize_text("")

        assert result == ""

    def test_whitespace_only_string_returns_empty_string(self) -> None:
        """A whitespace-only string normalizes to an empty string."""
        result = normalize_text("   \n\t  ")

        assert result == ""

    def test_text_with_no_special_content_is_unchanged(self) -> None:
        """Plain text with nothing to normalize is returned unchanged."""
        result = normalize_text("This is a perfectly normal sentence.")

        assert result == "This is a perfectly normal sentence."


class TestNormalizeSegment:
    """Tests for the NarrationSegment-level wrapper."""

    def test_returns_new_segment_with_normalized_text(self) -> None:
        """normalize_segment returns a new segment with normalized text."""
        segment = NarrationSegment(
            index=1, label="intro", text="Welcome to FireworksAI in 2026!!!"
        )

        result = normalize_segment(segment)

        assert isinstance(result, NarrationSegment)
        assert result.text == "Welcome to Fireworks AI in Twenty Twenty Six!"

    def test_preserves_index_and_label(self) -> None:
        """normalize_segment carries index and label through unchanged."""
        segment = NarrationSegment(index=3, label="history", text="MgSO4 facts.")

        result = normalize_segment(segment)

        assert result.index == 3
        assert result.label == "history"

    def test_original_segment_is_not_mutated(self) -> None:
        """The original NarrationSegment object is left untouched."""
        segment = NarrationSegment(index=0, label="intro", text="FireworksAI!!!")

        normalize_segment(segment)

        assert segment.text == "FireworksAI!!!"

    def test_custom_lookup_is_passed_through(self) -> None:
        """A custom acronym lookup passed to normalize_segment is applied."""
        segment = NarrationSegment(index=0, label="intro", text="Powered by AI.")

        result = normalize_segment(
            segment, acronym_lookup={"AI": "Artificial Intelligence"}
        )

        assert result.text == "Powered by Artificial Intelligence."
