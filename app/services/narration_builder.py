"""Narration builder service.

This module transforms a parsed :class:`~app.models.script.Script`
into an ordered sequence of :class:`~app.models.audio.NarrationSegment`
objects: one for the introduction, one per content section, and one
for the conclusion. It performs no text normalization, no
text-to-speech synthesis, no file I/O, and no pipeline orchestration —
those responsibilities belong to other Milestone 3 components.
"""

from __future__ import annotations

import re

from app.models.audio import NarrationSegment
from app.models.script import Script

_INTRODUCTION_LABEL = "introduction"
_CONCLUSION_LABEL = "conclusion"
_NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")


def build_narration_segments(script: Script) -> tuple[NarrationSegment, ...]:
    """Build an ordered tuple of narration segments from a Script.

    The narration order is always: introduction, then each content
    section in the order they appear in ``script.sections``, then the
    conclusion.

    Args:
        script: The parsed :class:`~app.models.script.Script` to
            convert into narration segments.

    Returns:
        An ordered tuple of :class:`~app.models.audio.NarrationSegment`
        instances, indexed from ``0`` (introduction) through
        ``len(script.sections) + 1`` (conclusion).
    """
    segments: list[NarrationSegment] = [
        NarrationSegment(
            index=0,
            label=_INTRODUCTION_LABEL,
            text=script.introduction,
        )
    ]

    for position, section in enumerate(script.sections, start=1):
        segments.append(
            NarrationSegment(
                index=position,
                label=_label_from_heading(section.heading, fallback_index=position),
                text=section.content,
            )
        )

    segments.append(
        NarrationSegment(
            index=len(script.sections) + 1,
            label=_CONCLUSION_LABEL,
            text=script.conclusion,
        )
    )

    return tuple(segments)


def _label_from_heading(heading: str, fallback_index: int) -> str:
    """Derive a short, filesystem-safe label from a section heading.

    Args:
        heading: The section heading text (e.g. ``"The Role of Metal Salts"``).
        fallback_index: The 1-based section position, used to build a
            fallback label if the heading contains no usable characters.

    Returns:
        A lowercase, hyphen-separated slug (e.g.
        ``"the-role-of-metal-salts"``), or ``"section-<fallback_index>"``
        if the heading yields no alphanumeric characters.
    """
    slug = _NON_ALNUM_PATTERN.sub("-", heading.strip().lower()).strip("-")
    return slug if slug else f"section-{fallback_index}"
