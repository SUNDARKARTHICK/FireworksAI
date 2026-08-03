"""Unit tests for the video assembly data models (Component 1).

Scope is intentionally limited to construction, immutability, and
field access for :class:`SubtitleCue`, :class:`VideoSegmentPlan`,
:class:`VideoAssemblyResult`, and :class:`VideoValidationResult`. No
timing math, formatting, or I/O is exercised here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models.script import Metadata, Script, Section
from app.models.video import (
    SubtitleCue,
    VideoAssemblyResult,
    VideoSegmentPlan,
    VideoValidationResult,
)


def _make_script() -> Script:
    """Build a minimal Script fixture for model tests."""
    return Script(
        metadata=Metadata(title="Test Lesson", author="Author", date="2026-07-30"),
        introduction="Intro text.",
        sections=(Section(heading="Topic", content="Section text."),),
        conclusion="Conclusion text.",
    )


class TestSubtitleCue:
    """Tests for :class:`SubtitleCue`."""

    def test_constructs_with_expected_fields(self) -> None:
        """A SubtitleCue holds all constructor arguments as attributes."""
        cue = SubtitleCue(index=0, start_seconds=0.0, end_seconds=3.5, text="Hello.")

        assert cue.index == 0
        assert cue.start_seconds == 0.0
        assert cue.end_seconds == 3.5
        assert cue.text == "Hello."

    def test_is_immutable(self) -> None:
        """SubtitleCue is a frozen dataclass and cannot be mutated."""
        cue = SubtitleCue(index=0, start_seconds=0.0, end_seconds=3.5, text="Hello.")

        with pytest.raises(AttributeError):
            cue.text = "Changed"  # type: ignore[misc]


class TestVideoSegmentPlan:
    """Tests for :class:`VideoSegmentPlan`."""

    def test_constructs_with_expected_fields(self) -> None:
        """A VideoSegmentPlan holds a cue plus audio/image paths."""
        cue = SubtitleCue(index=1, start_seconds=3.5, end_seconds=7.0, text="More.")
        plan = VideoSegmentPlan(
            index=1,
            label="history",
            audio_path=Path("content/audio/01_history.mp3"),
            image_path=Path("content/images/01_history.png"),
            subtitle=cue,
        )

        assert plan.index == 1
        assert plan.label == "history"
        assert plan.audio_path == Path("content/audio/01_history.mp3")
        assert plan.image_path == Path("content/images/01_history.png")
        assert plan.subtitle is cue

    def test_is_immutable(self) -> None:
        """VideoSegmentPlan is a frozen dataclass and cannot be mutated."""
        cue = SubtitleCue(index=0, start_seconds=0.0, end_seconds=1.0, text="Hi.")
        plan = VideoSegmentPlan(
            index=0,
            label="intro",
            audio_path=Path("a.mp3"),
            image_path=Path("a.png"),
            subtitle=cue,
        )

        with pytest.raises(AttributeError):
            plan.label = "changed"  # type: ignore[misc]


class TestVideoAssemblyResult:
    """Tests for :class:`VideoAssemblyResult`."""

    def test_constructs_with_expected_fields(self) -> None:
        """A VideoAssemblyResult references the script and its segments."""
        script = _make_script()
        cue = SubtitleCue(index=0, start_seconds=0.0, end_seconds=2.0, text="Hi.")
        plan = VideoSegmentPlan(
            index=0,
            label="intro",
            audio_path=Path("a.mp3"),
            image_path=Path("a.png"),
            subtitle=cue,
        )

        result = VideoAssemblyResult(
            script=script,
            segments=(plan,),
            output_path=Path("content/output/phase01.mp4"),
            total_duration_seconds=2.0,
        )

        assert result.script is script
        assert result.segments == (plan,)
        assert result.output_path == Path("content/output/phase01.mp4")
        assert result.total_duration_seconds == 2.0

    def test_is_immutable(self) -> None:
        """VideoAssemblyResult is a frozen dataclass and cannot be mutated."""
        script = _make_script()
        result = VideoAssemblyResult(
            script=script,
            segments=(),
            output_path=Path("out.mp4"),
            total_duration_seconds=0.0,
        )

        with pytest.raises(AttributeError):
            result.total_duration_seconds = 10.0  # type: ignore[misc]


class TestVideoValidationResult:
    """Tests for :class:`VideoValidationResult`."""

    def test_constructs_with_expected_fields_for_valid_video(self) -> None:
        """A passing VideoValidationResult has no errors."""
        result = VideoValidationResult(
            video_path=Path("out.mp4"),
            is_valid=True,
            duration_seconds=12.5,
            checks_performed=("file_exists", "non_empty"),
            errors=(),
        )

        assert result.is_valid is True
        assert result.duration_seconds == 12.5
        assert result.checks_performed == ("file_exists", "non_empty")
        assert result.errors == ()

    def test_constructs_with_expected_fields_for_invalid_video(self) -> None:
        """A failing VideoValidationResult carries error messages."""
        result = VideoValidationResult(
            video_path=Path("missing.mp4"),
            is_valid=False,
            duration_seconds=None,
            checks_performed=("file_exists",),
            errors=("File does not exist.",),
        )

        assert result.is_valid is False
        assert result.duration_seconds is None
        assert result.errors == ("File does not exist.",)

    def test_is_immutable(self) -> None:
        """VideoValidationResult is a frozen dataclass and cannot be mutated."""
        result = VideoValidationResult(
            video_path=Path("out.mp4"),
            is_valid=True,
            duration_seconds=1.0,
            checks_performed=(),
            errors=(),
        )

        with pytest.raises(AttributeError):
            result.is_valid = False  # type: ignore[misc]
