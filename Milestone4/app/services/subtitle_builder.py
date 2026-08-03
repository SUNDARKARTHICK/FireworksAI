"""Subtitle cue timing builder service.

This module converts an ordered sequence of narrated audio segments
(Milestone 3's :class:`~app.models.audio.AudioSegment`) into an
ordered sequence of timed subtitle cues
(:class:`~app.models.video.SubtitleCue`), by accumulating each
segment's real audio duration into start/end timestamps.

This module performs no duration probing and no FFmpeg invocation -
it assumes every input segment's ``duration_seconds`` has already
been populated by whichever component measured the real audio file
(``app.services.ffmpeg_service``, in a later Milestone 4 component).
It is a pure, synchronous, deterministic computation with no file
I/O and no network access.
"""

from __future__ import annotations

from app.exceptions import SubtitleTimingError
from app.models.audio import AudioSegment
from app.models.video import SubtitleCue


def build_subtitle_cues(
    audio_segments: tuple[AudioSegment, ...],
) -> tuple[SubtitleCue, ...]:
    """Build ordered, cumulatively-timed subtitle cues from audio segments.

    Each cue's ``start_seconds`` is the running total of every prior
    segment's duration; its ``end_seconds`` is that start plus its own
    segment's duration. The first cue therefore always starts at
    ``0.0``.

    Args:
        audio_segments: An ordered tuple of narrated audio segments,
            in the order they should appear in the final video. Each
            segment's ``duration_seconds`` must already be populated
            with a positive value.

    Returns:
        An ordered tuple of :class:`~app.models.video.SubtitleCue`
        instances, one per input segment, carrying through each
        segment's ``index`` and narration text alongside its computed
        timing.

    Raises:
        SubtitleTimingError: If any segment's ``duration_seconds`` is
            ``None`` or not strictly positive.
    """
    cues: list[SubtitleCue] = []
    current_start_seconds = 0.0

    for audio_segment in audio_segments:
        duration_seconds = audio_segment.duration_seconds

        if duration_seconds is None or duration_seconds <= 0:
            raise SubtitleTimingError(
                f"Audio segment '{audio_segment.segment.label}' (index "
                f"{audio_segment.segment.index}) has an invalid "
                f"duration ({duration_seconds!r}); duration_seconds "
                "must be a populated, positive value before building "
                "subtitle cues."
            )

        end_seconds = current_start_seconds + duration_seconds
        cues.append(
            SubtitleCue(
                index=audio_segment.segment.index,
                start_seconds=current_start_seconds,
                end_seconds=end_seconds,
                text=audio_segment.segment.text,
            )
        )
        current_start_seconds = end_seconds

    return tuple(cues)
