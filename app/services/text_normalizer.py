"""Text normalization service for narration segments.

This module prepares narration text for text-to-speech synthesis by
expanding known acronyms/brand names, spelling out bare 4-digit years,
and cleaning up punctuation and whitespace. It is a pure, synchronous
transformation with no file I/O, no network calls, no text-to-speech
calls, and no pipeline orchestration.

Scope is intentionally limited to rule-based, table-driven
normalization. It does not implement general natural-language
processing, AI-based text rewriting, a general number-to-words engine,
or a phoneme/pronunciation engine.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from app.models.audio import NarrationSegment

#: Default acronym/brand-name expansion table. Callers may override
#: this via the ``acronym_lookup`` parameter of :func:`normalize_text`
#: or :func:`normalize_segment` without modifying this module.
DEFAULT_ACRONYM_LOOKUP: Mapping[str, str] = {
    "FireworksAI": "Fireworks AI",
    "MgSO4": "Magnesium Sulfate",
    "TTS": "Text To Speech",
}

_ONES = (
    "zero", "one", "two", "three", "four",
    "five", "six", "seven", "eight", "nine",
)
_TEENS = (
    "ten", "eleven", "twelve", "thirteen", "fourteen",
    "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
)
_TENS = (
    "zero", "ten", "twenty", "thirty", "forty",
    "fifty", "sixty", "seventy", "eighty", "ninety",
)

_YEAR_PATTERN = re.compile(r"\b([12]\d{3})\b")
_REPEATED_PUNCTUATION_PATTERN = re.compile(r"([!?,;:])\1+")
_LONG_ELLIPSIS_PATTERN = re.compile(r"\.{4,}")
_SPACE_BEFORE_PUNCTUATION_PATTERN = re.compile(r"\s+([!?,;:.])")
_WHITESPACE_RUN_PATTERN = re.compile(r"\s+")


def normalize_segment(
    segment: NarrationSegment,
    acronym_lookup: Mapping[str, str] | None = None,
) -> NarrationSegment:
    """Return a new NarrationSegment with pronunciation-normalized text.

    Args:
        segment: The source narration segment whose ``text`` should be
            normalized. ``index`` and ``label`` are carried through
            unchanged.
        acronym_lookup: Optional mapping of exact substrings to their
            spoken expansions. Defaults to :data:`DEFAULT_ACRONYM_LOOKUP`
            when not provided.

    Returns:
        A new :class:`~app.models.audio.NarrationSegment` with the
        same ``index`` and ``label``, and normalized ``text``.
    """
    normalized_text = normalize_text(segment.text, acronym_lookup=acronym_lookup)
    return NarrationSegment(
        index=segment.index,
        label=segment.label,
        text=normalized_text,
    )


def normalize_text(
    text: str,
    acronym_lookup: Mapping[str, str] | None = None,
) -> str:
    """Normalize raw narration text for pronunciation-friendly speech.

    Applies, in order: acronym/brand-name expansion, bare 4-digit year
    expansion, punctuation cleanup, and whitespace cleanup.

    Args:
        text: The raw narration text to normalize.
        acronym_lookup: Optional mapping of exact substrings to their
            spoken expansions. Defaults to :data:`DEFAULT_ACRONYM_LOOKUP`
            when not provided.

    Returns:
        The normalized, speakable text.
    """
    lookup = acronym_lookup if acronym_lookup is not None else DEFAULT_ACRONYM_LOOKUP

    result = _expand_acronyms(text, lookup)
    result = _expand_years(result)
    result = _cleanup_punctuation(result)
    result = _cleanup_whitespace(result)
    return result


def _expand_acronyms(text: str, lookup: Mapping[str, str]) -> str:
    """Replace exact acronym/brand-name matches with their expansions.

    Args:
        text: The text to search for acronyms.
        lookup: Mapping of exact substrings to their spoken expansions.
            Longer keys are matched before shorter keys to avoid a
            short key partially matching inside a longer one.

    Returns:
        The text with all matched acronyms replaced by their
        expansions.
    """
    result = text
    for term in sorted(lookup, key=len, reverse=True):
        pattern = re.compile(rf"\b{re.escape(term)}\b")
        result = pattern.sub(lookup[term], result)
    return result


def _expand_years(text: str) -> str:
    """Replace bare 4-digit years with their spoken word form.

    Args:
        text: The text to search for standalone 4-digit years (1000-2999).

    Returns:
        The text with each matched year replaced by its spoken form
        (e.g. ``"2026"`` becomes ``"Twenty Twenty Six"``).
    """
    return _YEAR_PATTERN.sub(lambda match: _year_to_words(int(match.group(1))), text)


def _year_to_words(year: int) -> str:
    """Convert a 4-digit year into a simple, rule-based spoken form.

    The year is split into two 2-digit groups (e.g. ``2026`` -> ``20``
    and ``26``) and each group is converted independently. This is a
    deliberately simple, rule-based approach for common calendar
    years — not a general-purpose number-to-words engine.

    Args:
        year: A 4-digit integer between 1000 and 2999.

    Returns:
        The spoken form of the year, e.g. ``"Twenty Twenty Six"``.
    """
    first_group, second_group = divmod(year, 100)

    first_words = _two_digit_to_words(first_group)

    if second_group == 0:
        return f"{first_words} Hundred"
    if second_group < 10:
        return f"{first_words} Oh {_ONES[second_group].title()}"
    return f"{first_words} {_two_digit_to_words(second_group)}"


def _two_digit_to_words(number: int) -> str:
    """Convert an integer from 0-99 into title-cased spoken words.

    Args:
        number: An integer in the range 0-99.

    Returns:
        The spoken word form, e.g. ``20`` -> ``"Twenty"``,
        ``26`` -> ``"Twenty Six"``.
    """
    if number < 10:
        return _ONES[number].title()
    if number < 20:
        return _TEENS[number - 10].title()

    tens_digit, ones_digit = divmod(number, 10)
    tens_words = _TENS[tens_digit].title()
    if ones_digit == 0:
        return tens_words
    return f"{tens_words} {_ONES[ones_digit].title()}"


def _cleanup_punctuation(text: str) -> str:
    """Collapse repeated punctuation and remove stray pre-punctuation spaces.

    Args:
        text: The text to clean.

    Returns:
        The text with runs of repeated punctuation collapsed to a
        single character, long dot-runs collapsed to a standard
        ellipsis, and whitespace immediately before punctuation
        removed.
    """
    result = _LONG_ELLIPSIS_PATTERN.sub("...", text)
    result = _REPEATED_PUNCTUATION_PATTERN.sub(r"\1", result)
    result = _SPACE_BEFORE_PUNCTUATION_PATTERN.sub(r"\1", result)
    return result


def _cleanup_whitespace(text: str) -> str:
    """Collapse whitespace runs and strip leading/trailing whitespace.

    Args:
        text: The text to clean.

    Returns:
        The text with every run of whitespace collapsed to a single
        space, and leading/trailing whitespace removed.
    """
    return _WHITESPACE_RUN_PATTERN.sub(" ", text).strip()
