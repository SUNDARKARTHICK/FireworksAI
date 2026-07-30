"""Data models representing a parsed lesson script.

This module defines pure data containers only: :class:`Metadata`,
:class:`Section`, and :class:`Script`. It contains no parsing logic,
no validation logic, and no file I/O. Building and validating these
objects is the responsibility of :mod:`app.services.markdown_parser`.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Metadata:
    """Descriptive metadata for a lesson script, sourced from YAML front matter.

    Attributes:
        title: The title of the lesson.
        author: The author of the lesson content.
        date: The publication or authoring date, as a string (e.g.
            ``"2026-07-30"``).
        language: ISO language code for the lesson content.
        voice: Optional text-to-speech voice identifier associated
            with this lesson.
        tags: Optional tuple of topical tags associated with the lesson.
    """

    title: str
    author: str
    date: str
    language: str = "en"
    voice: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Section:
    """A single named content section within a lesson script.

    Attributes:
        heading: The section's heading text (e.g. ``"History of Fireworks"``).
        content: The section's body text.
    """

    heading: str
    content: str


@dataclass(frozen=True, slots=True)
class Script:
    """A complete parsed lesson script.

    Attributes:
        metadata: The lesson's descriptive :class:`Metadata`.
        introduction: The introduction text of the lesson.
        sections: An ordered tuple of content :class:`Section` objects.
        conclusion: The conclusion text of the lesson.
    """

    metadata: Metadata
    introduction: str
    sections: tuple[Section, ...]
    conclusion: str
