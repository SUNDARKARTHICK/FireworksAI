"""Deterministic filename generation for narration segments.

This module produces path-safe filename strings for
:class:`~app.models.audio.NarrationSegment` instances. It performs no
filesystem access of any kind — no directory creation, no file
writing, no existence checks. Writing files is the responsibility of
:mod:`app.services.audio_writer`.

Basename generation (the ``"<index>_<label>"`` portion, shared with
other media types like images) is delegated to
:mod:`app.utils.segment_namer`; this module only adds the audio-specific
extension.
"""

from __future__ import annotations

from app.models.audio import NarrationSegment
from app.utils.segment_namer import build_segment_basename

_DEFAULT_EXTENSION = "mp3"


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
    basename = build_segment_basename(segment.index, segment.label)
    clean_extension = extension.lstrip(".").lower()
    return f"{basename}.{clean_extension}"

