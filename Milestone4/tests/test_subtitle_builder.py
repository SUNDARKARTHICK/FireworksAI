"""Unit tests for the subtitle cue timing builder (Component 2).

Scope is intentionally limited to
:func:`app.services.subtitle_builder.build_subtitle_cues`. No file
I/O, no FFmpeg invocation, and no duration probing are exercised here
- fixtures directly construct AudioSegment instances with
pre-populated durations.
"""

from __future__ import annotations

import pytest

from app.exceptions import SubtitleTimingError
from app.models.audio import AudioSegment, NarrationSegment
from app.models.video import SubtitleCue
from app.services.subtitle_builder import build_subtitle_cues


def _make_audio_segment(
    index: int, label: str, text: str, duration_seconds: float | None
) -> AudioSegment:
    """Build an AudioSegment fixture with a given duration."""
    return AudioSegment(
        segment=NarrationSegment(index=index, label=label, text=text),
        file_path=None,  # type: ignore[arg-type]
        duration_seconds=duration_seconds,
    )


class TestBuildSubtitleCues:
    """Tests for :func:`build_subtitle_cues`."""

    def test_returns_tuple_of_subtitle_cues(self) -> None:
        """The builder returns a tuple of SubtitleCue instances."""
        segments = (_make_audio_segment(0, "introduction", "Hello.", 4.0),)

        cues = build_subtitle_cues(segments)

        assert isinstance(cues, tuple)
        assert all(isinstance(cue, SubtitleCue) for cue in cues)

    def test_first_cue_starts_at_zero(self) -> None:
        """The first cue always begins at 0.0 seconds."""
        segments = (_make_audio_segment(0, "introduction", "Hello.", 5.0),)

        cues = build_subtitle_cues(segments)

        assert cues[0].start_seconds == 0.0
        assert cues[0].end_seconds == 5.0

    def test_cumulative_timing_across_multiple_segments(self) -> None:
        """Each subsequent cue starts where the previous one ended."""
        segments = (
            _make_audio_segment(0, "introduction", "Intro text.", 4.2),
            _make_audio_segment(1, "history", "History text.", 6.8),
            _make_audio_segment(2, "conclusion", "Conclusion text.", 3.0),
        )

        cues = build_subtitle_cues(segments)

        assert cues[0].start_seconds == 0.0
        assert cues[0].end_seconds == pytest.approx(4.2)
        assert cues[1].start_seconds == pytest.approx(4.2)
        assert cues[1].end_seconds == pytest.approx(11.0)
        assert cues[2].start_seconds == pytest.approx(11.0)
        assert cues[2].end_seconds == pytest.approx(14.0)

    def test_index_and_text_are_preserved(self) -> None:
        """Each cue carries through its source segment's index and text."""
        segments = (
            _make_audio_segment(0, "introduction", "Intro text.", 2.0),
            _make_audio_segment(1, "history", "History text.", 3.0),
        )

        cues = build_subtitle_cues(segments)

        assert cues[0].index == 0
        assert cues[0].text == "Intro text."
        assert cues[1].index == 1
        assert cues[1].text == "History text."

    def test_single_segment_produces_single_cue(self) -> None:
        """A single audio segment produces exactly one subtitle cue."""
        segments = (_make_audio_segment(0, "introduction", "Hi.", 1.5),)

        cues = build_subtitle_cues(segments)

        assert len(cues) == 1

    def test_empty_input_returns_empty_tuple(self) -> None:
        """An empty input tuple returns an empty output tuple."""
        cues = build_subtitle_cues(())

        assert cues == ()

    def test_none_duration_raises_subtitle_timing_error(self) -> None:
        """A segment with duration_seconds=None raises SubtitleTimingError."""
        segments = (_make_audio_segment(0, "introduction", "Hi.", None),)

        with pytest.raises(SubtitleTimingError, match="invalid duration"):
            build_subtitle_cues(segments)

    def test_zero_duration_raises_subtitle_timing_error(self) -> None:
        """A segment with duration_seconds=0 raises SubtitleTimingError."""
        segments = (_make_audio_segment(0, "introduction", "Hi.", 0.0),)

        with pytest.raises(SubtitleTimingError, match="invalid duration"):
            build_subtitle_cues(segments)

    def test_negative_duration_raises_subtitle_timing_error(self) -> None:
        """A segment with a negative duration raises SubtitleTimingError."""
        segments = (_make_audio_segment(0, "introduction", "Hi.", -2.0),)

        with pytest.raises(SubtitleTimingError, match="invalid duration"):
            build_subtitle_cues(segments)

    def test_error_identifies_the_failing_segment(self) -> None:
        """The error message names the specific segment that failed."""
        segments = (
            _make_audio_segment(0, "introduction", "Hi.", 2.0),
            _make_audio_segment(1, "history", "History text.", None),
        )

        with pytest.raises(SubtitleTimingError, match="history"):
            build_subtitle_cues(segments)

    def test_is_deterministic_for_the_same_input(self) -> None:
        """Calling build_subtitle_cues twice with the same input is stable."""
        segments = (
            _make_audio_segment(0, "introduction", "Hi.", 2.0),
            _make_audio_segment(1, "history", "History text.", 3.0),
        )

        first = build_subtitle_cues(segments)
        second = build_subtitle_cues(segments)

        assert first == second
