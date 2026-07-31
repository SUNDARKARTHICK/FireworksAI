"""Data models for audio narration generation.

This module defines pure data containers only: :class:`NarrationSegment`,
:class:`AudioSegment`, and :class:`AudioGenerationResult`. It contains
no text normalization, no text-to-speech logic, and no file I/O.
Building and populating these objects is the responsibility of the
Milestone 3 services (``narration_builder``, ``text_normalizer``,
``tts_service``, ``audio_writer``) and the ``audio_pipeline``
orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.models.script import Script


@dataclass(frozen=True, slots=True)
class NarrationSegment:
    """A single ordered unit of narration text extracted from a Script.

    Attributes:
        index: Zero-based position of this segment within the full
            narration sequence (e.g. ``0`` for the introduction).
        label: A short, stable, filesystem-safe identifier for this
            segment's content (e.g. ``"introduction"``,
            ``"history"``, ``"conclusion"``). Does not include any
            numeric prefix or file extension.
        text: The raw narration text for this segment, as extracted
            from the source :class:`~app.models.script.Script`,
            before any pronunciation normalization is applied.
    """

    index: int
    label: str
    text: str


@dataclass(frozen=True, slots=True)
class AudioSegment:
    """A narration segment paired with its rendered audio file.

    Attributes:
        segment: The source :class:`NarrationSegment` this audio was
            rendered from.
        file_path: Path to the rendered audio file on disk (one file
            per segment, per the one-file-per-segment convention).
        duration_seconds: Optional duration of the rendered audio, in
            seconds. Reserved for a future milestone that measures
            audio duration (e.g. for FFmpeg synchronization); left
            unset (``None``) by Milestone 3.
    """

    segment: NarrationSegment
    file_path: Path
    duration_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class AudioGenerationResult:
    """The complete outcome of narrating a Script into audio segments.

    Attributes:
        script: The source :class:`~app.models.script.Script` that was
            narrated.
        segments: An ordered tuple of :class:`AudioSegment` objects,
            one per narration segment, in narration order.
    """

    script: Script
    segments: tuple[AudioSegment, ...]
