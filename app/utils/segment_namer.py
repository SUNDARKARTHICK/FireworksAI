"""Shared, media-agnostic segment basename generation.

This module computes the deterministic ``"<index>_<label>"`` basename
shared by every per-segment media file (audio, image, and any future
media type), independent of file extension. Extraction here means
filename *policy* (zero-padded index + sanitized label) is defined
exactly once, while each media-specific component (e.g.
:mod:`app.services.audio_writer`, :mod:`app.services.image_loader`)
independently controls which extension(s) it appends. This module
performs no filesystem access of any kind.
"""

from __future__ import annotations

import re

_UNSAFE_CHAR_PATTERN = re.compile(r"[^a-z0-9\-]+")
_INDEX_WIDTH = 2
_FALLBACK_LABEL = "segment"


def build_segment_basename(index: int, label: str) -> str:
    """Build a deterministic, path-safe basename for a segment.

    The basename takes the form ``"<zero-padded-index>_<label>"``,
    e.g. ``"00_introduction"`` or ``"01_history-of-fireworks"``. It
    intentionally excludes any file extension — callers append their
    own media-specific extension(s).

    Args:
        index: Zero-based position of the segment within its
            sequence.
        label: A short, human-readable label describing the segment's
            content (e.g. ``"introduction"``, ``"History of Fireworks"``).

    Returns:
        A deterministic, path-safe basename string containing only
        lowercase letters, digits, underscores, and hyphens.
    """
    sanitized_label = _sanitize_label(label)
    return f"{index:0{_INDEX_WIDTH}d}_{sanitized_label}"


def _sanitize_label(label: str) -> str:
    """Sanitize a label into a lowercase, path-safe slug.

    Args:
        label: The raw label to sanitize.

    Returns:
        A lowercase string containing only ``a-z``, ``0-9``, and
        hyphens, with no leading/trailing hyphens. Falls back to
        ``"segment"`` if sanitization removes all characters.
    """
    lowered = label.strip().lower()
    sanitized = _UNSAFE_CHAR_PATTERN.sub("-", lowered).strip("-")
    return sanitized if sanitized else _FALLBACK_LABEL
