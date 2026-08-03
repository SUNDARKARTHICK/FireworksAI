"""Data models for video assembly.

This module defines pure data containers only: :class:`SubtitleCue`,
:class:`VideoSegmentPlan`, :class:`VideoAssemblyResult`, and
:class:`VideoValidationResult`. It contains no timing math, no
subtitle formatting, no FFmpeg invocation, no path resolution logic,
and no file I/O. Building and populating these objects is the
responsibility of the Milestone 4 services (``subtitle_builder``,
``image_loader``, ``ffmpeg_service``, ``video_validator``) and the
``video_pipeline`` orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.models.script import Script


@dataclass(frozen=True, slots=True)
class SubtitleCue:
    """A single timed subtitle caption.

    Attributes:
        index: Zero-based position of this cue within the full
            subtitle sequence, matching the corresponding narration
            segment's index.
        start_seconds: The time, in seconds from the start of the
            video, at which this cue should appear.
        end_seconds: The time, in seconds from the start of the video,
            at which this cue should disappear. Must be greater than
            ``start_seconds``.
        text: The caption text to display during this cue's interval.
    """

    index: int
    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True, slots=True)
class VideoSegmentPlan:
    """Everything needed to render one segment of the final video.

    Design note:
        This class intentionally stores ``audio_path`` and
        ``image_path`` as plain :class:`pathlib.Path` values rather
        than embedding Milestone 3's
        :class:`~app.models.audio.AudioSegment` object directly.
        FFmpeg (and everything in this milestone) only ever needs a
        file path to read from -- pulling in the full ``AudioSegment``
        would also drag along its nested ``NarrationSegment`` and
        couple Milestone 4 to Milestone 3's model internals more
        tightly than necessary. Storing plain paths keeps this
        milestone's only cross-milestone model dependency limited to
        :class:`~app.models.script.Script`, so a future change to
        ``AudioSegment`` (e.g. Milestone 3 gaining new fields) cannot
        ripple into video assembly.

    Attributes:
        index: Zero-based position of this segment within the video.
        label: A short, stable identifier for this segment (e.g.
            ``"introduction"``, ``"history-of-fireworks"``), carried
            through from the corresponding narration segment.
        audio_path: Path to this segment's narrated audio file on
            disk (produced in Milestone 3).
        image_path: Path to the image to display during this
            segment's audio.
        subtitle: The :class:`SubtitleCue` corresponding to this
            segment.
    """

    index: int
    label: str
    audio_path: Path
    image_path: Path
    subtitle: SubtitleCue


@dataclass(frozen=True, slots=True)
class VideoAssemblyResult:
    """The complete outcome of assembling a Script into a video.

    Attributes:
        script: The source :class:`~app.models.script.Script` that was
            rendered into video.
        segments: An ordered tuple of :class:`VideoSegmentPlan` objects
            used to render the video, in video order.
        output_path: Path to the final rendered MP4 file on disk.
        total_duration_seconds: The total duration of the rendered
            video, in seconds.
    """

    script: Script
    segments: tuple[VideoSegmentPlan, ...]
    output_path: Path
    total_duration_seconds: float


@dataclass(frozen=True, slots=True)
class VideoValidationResult:
    """The outcome of validating a rendered video file.

    Attributes:
        video_path: Path to the video file that was validated.
        is_valid: Whether the video passed all validation checks.
        duration_seconds: The measured duration of the video, in
            seconds, or ``None`` if duration could not be measured.
        checks_performed: An ordered tuple naming each validation
            check that was run (e.g. ``"file_exists"``,
            ``"non_empty"``, ``"duration_matches_expected"``).
        errors: An ordered tuple of human-readable error messages for
            any checks that failed. Empty when ``is_valid`` is
            ``True``.
    """

    video_path: Path
    is_valid: bool
    duration_seconds: float | None
    checks_performed: tuple[str, ...]
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ImageAsset:
    """A single image file matched to one video segment.

    Added for Component 3 (``app.services.image_loader``), which
    requires a typed, immutable return value distinct from a bare
    :class:`pathlib.Path`.

    Attributes:
        index: Zero-based position of this image within the video
            segment sequence, matching the corresponding narration
            segment's index.
        file_path: Path to the discovered image file on disk.
    """

    index: int
    file_path: Path

