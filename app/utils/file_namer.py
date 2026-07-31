"""Deterministic filename generation for narration segments.

This module produces path-safe filename strings for
:class:`~app.models.audio.NarrationSegment` instances. It performs no
filesystem access of any kind — no directory creation, no file
writing, no existence checks. Writing files is the responsibility of
:mod:`app.services.audio_writer`.
"""

from __future__ import annotations

import re

from app.models.audio import NarrationSegment

_UNSAFE_CHAR_PATTERN = re.compile(r"[^a-z0-9\-]+")
_DEFAULT_EXTENSION = "mp3"
_INDEX_WIDTH = 2


def build_filename(segment: NarrationSegment, extension: str = _DEFAULT_EXTENSION) -> str:
    """Build a deterministic, path-safe filename for a narration segment.

    The filename takes the form ``"<zero-padded-index>_<label>.<extension>"``,
    e.g. ``"00_introduction.mp3"`` or ``"01_history-of-fireworks.mp3"``.
    The same segment always produces the same filename.

    Args:
        segment: The narration segment to generate a filename for.
        extension: The file extension to use, with or without a
            leading dot (e.g. ``"mp3"`` or ``".mp3"``). Defaults to
            ``"mp3"``.

    Returns:
        A deterministic, path-safe filename string.
    """
    sanitized_label = _sanitize_label(segment.label)
    clean_extension = extension.lstrip(".").lower()
    return f"{segment.index:0{_INDEX_WIDTH}d}_{sanitized_label}.{clean_extension}"


def _sanitize_label(label: str) -> str:
    """Sanitize a segment label into a lowercase, path-safe slug.

    This is a defensive safeguard: even though
    :mod:`app.services.narration_builder` already produces slugified
    labels, this function guarantees path-safety independently, in
    case a label originates from elsewhere in the future.

    Args:
        label: The raw label to sanitize.

    Returns:
        A lowercase string containing only ``a-z``, ``0-9``, and
        hyphens, with no leading/trailing hyphens. Falls back to
        ``"segment"`` if sanitization removes all characters.
    """
    lowered = label.strip().lower()
    sanitized = _UNSAFE_CHAR_PATTERN.sub("-", lowered).strip("-")
    return sanitized if sanitized else "segment"
