"""
Audio Model

Purpose:
    Represents audio-related data structures used across milestones.

Responsibilities:
    - Define data containers for audio files and narrated segments

This module intentionally contains only dataclasses and no I/O or
business logic. New Milestone 4 dataclasses were added here so the
pipeline and services can consistently import audio-related types from
one place.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple, Optional

from app.models.script import Script


@dataclass(slots=True)
class Audio:
    """
    Represents a generated audio file.

    Attributes:
        filename: Name of the audio file.
        file_path: Full path to the generated audio file.
        format: Audio format (e.g., mp3).
        duration: Duration of the audio in seconds.
        voice: Voice used for narration.
        language: Language of the narration.
    """

    filename: str
    file_path: Path
    format: str
    duration: float
    voice: str
    language: str


# ---------------------------------------------------------------------------
# Milestone 3 / 4 models (Narration / AudioSegment / AudioGenerationResult)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class NarrationSegment:
    """A single narration segment produced from the source Script.

    Attributes:
        index: Zero-based index of the segment within the script.
        label: Short label used for deterministic filenames.
        text: The narration text for this segment.
    """

    index: int
    label: str
    text: str


@dataclass(frozen=True, slots=True)
class AudioSegment:
    """A narrated audio segment produced by the TTS engine.

    Attributes:
        segment: The source :class:`NarrationSegment` this audio corresponds to.
        file_path: Path to the generated audio file on disk.
        duration_seconds: Measured duration in seconds (may be None until probed).
    """

    segment: NarrationSegment
    file_path: Path
    duration_seconds: Optional[float]


@dataclass(frozen=True)
class AudioGenerationResult:
    """Container for the output of the audio generation step.

    Attributes:
        script: The source :class:`app.models.script.Script` used to
            produce the narrated segments.
        segments: An ordered tuple of :class:`AudioSegment` entries.
    """

    script: Script
    segments: Tuple[AudioSegment, ...] = field(default_factory=tuple)
