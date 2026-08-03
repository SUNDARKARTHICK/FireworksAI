"""Unit tests for the video validation service (Component 5).

Scope is intentionally limited to
:class:`app.services.video_validator.VideoValidator`. No real FFmpeg
is ever executed - all duration measurement is delegated to an
injected fake :class:`DurationProbe`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.exceptions import VideoValidationError
from app.models.video import VideoValidationResult
from app.services.video_validator import DurationProbe, VideoValidator


class _FakeDurationProbe:
    """A fake DurationProbe returning a configured, canned duration."""

    def __init__(self, duration_seconds: float | None = None, error: Exception | None = None) -> None:
        self._duration_seconds = duration_seconds
        self._error = error
        self.calls: list[Path] = []

    def probe_duration(self, path: Path) -> float:
        self.calls.append(path)
        if self._error is not None:
            raise self._error
        assert self._duration_seconds is not None
        return self._duration_seconds


def _make_mp4(tmp_path: Path, name: str = "final.mp4", size_bytes: int = 100) -> Path:
    """Create a non-empty dummy .mp4 file."""
    path = tmp_path / name
    path.write_bytes(b"x" * size_bytes)
    return path


class TestDurationProbeProtocol:
    """Tests verifying the DurationProbe Protocol contract."""

    def test_fake_probe_satisfies_protocol(self) -> None:
        """The fake test double structurally satisfies DurationProbe."""
        probe: DurationProbe = _FakeDurationProbe(duration_seconds=10.0)

        assert isinstance(probe, DurationProbe)


class TestValidVideo:
    """Tests for a fully valid video."""

    def test_returns_valid_result(self, tmp_path: Path) -> None:
        """A video matching all checks returns a valid VideoValidationResult."""
        video_path = _make_mp4(tmp_path)
        probe = _FakeDurationProbe(duration_seconds=10.0)
        validator = VideoValidator(duration_probe=probe)

        result = validator.validate(video_path, expected_duration_seconds=10.0)

        assert isinstance(result, VideoValidationResult)
        assert result.is_valid is True
        assert result.video_path == video_path
        assert result.duration_seconds == 10.0
        assert result.errors == ()

    def test_checks_performed_lists_all_checks(self, tmp_path: Path) -> None:
        """A fully valid video records every check that was performed."""
        video_path = _make_mp4(tmp_path)
        probe = _FakeDurationProbe(duration_seconds=10.0)
        validator = VideoValidator(duration_probe=probe)

        result = validator.validate(video_path, expected_duration_seconds=10.0)

        assert result.checks_performed == (
            "file_exists",
            "extension",
            "non_empty",
            "duration_probe",
            "duration_positive",
            "duration_matches_expected",
        )

    def test_probe_is_called_with_video_path(self, tmp_path: Path) -> None:
        """The injected duration probe is called with the video's path."""
        video_path = _make_mp4(tmp_path)
        probe = _FakeDurationProbe(duration_seconds=5.0)
        validator = VideoValidator(duration_probe=probe)

        validator.validate(video_path, expected_duration_seconds=5.0)

        assert probe.calls == [video_path]


class TestMissingFile:
    """Tests for a missing video file."""

    def test_missing_file_raises_video_validation_error(self, tmp_path: Path) -> None:
        """A non-existent video file raises VideoValidationError."""
        missing_path = tmp_path / "does_not_exist.mp4"
        probe = _FakeDurationProbe(duration_seconds=10.0)
        validator = VideoValidator(duration_probe=probe)

        with pytest.raises(VideoValidationError, match="not found"):
            validator.validate(missing_path, expected_duration_seconds=10.0)

    def test_missing_file_does_not_call_duration_probe(self, tmp_path: Path) -> None:
        """A missing file fails fast without ever calling the duration probe."""
        missing_path = tmp_path / "does_not_exist.mp4"
        probe = _FakeDurationProbe(duration_seconds=10.0)
        validator = VideoValidator(duration_probe=probe)

        with pytest.raises(VideoValidationError):
            validator.validate(missing_path, expected_duration_seconds=10.0)

        assert probe.calls == []


class TestWrongExtension:
    """Tests for an incorrect file extension."""

    def test_wrong_extension_raises_video_validation_error(self, tmp_path: Path) -> None:
        """A non-.mp4 extension raises VideoValidationError."""
        video_path = _make_mp4(tmp_path, name="final.mkv")
        probe = _FakeDurationProbe(duration_seconds=10.0)
        validator = VideoValidator(duration_probe=probe)

        with pytest.raises(VideoValidationError, match="extension"):
            validator.validate(video_path, expected_duration_seconds=10.0)

    def test_extension_check_is_case_insensitive(self, tmp_path: Path) -> None:
        """An uppercase .MP4 extension is accepted."""
        video_path = _make_mp4(tmp_path, name="final.MP4")
        probe = _FakeDurationProbe(duration_seconds=10.0)
        validator = VideoValidator(duration_probe=probe)

        result = validator.validate(video_path, expected_duration_seconds=10.0)

        assert result.is_valid is True


class TestEmptyFile:
    """Tests for an empty video file."""

    def test_empty_file_raises_video_validation_error(self, tmp_path: Path) -> None:
        """A zero-byte video file raises VideoValidationError."""
        video_path = _make_mp4(tmp_path, size_bytes=0)
        probe = _FakeDurationProbe(duration_seconds=10.0)
        validator = VideoValidator(duration_probe=probe)

        with pytest.raises(VideoValidationError, match="empty"):
            validator.validate(video_path, expected_duration_seconds=10.0)


class TestDurationMismatch:
    """Tests for a duration mismatch beyond tolerance."""

    def test_duration_mismatch_raises_video_validation_error(self, tmp_path: Path) -> None:
        """A measured duration far from expected raises VideoValidationError."""
        video_path = _make_mp4(tmp_path)
        probe = _FakeDurationProbe(duration_seconds=20.0)
        validator = VideoValidator(duration_probe=probe, tolerance_seconds=0.5)

        with pytest.raises(VideoValidationError, match="differs from expected"):
            validator.validate(video_path, expected_duration_seconds=10.0)


class TestZeroDuration:
    """Tests for a zero measured duration."""

    def test_zero_duration_raises_video_validation_error(self, tmp_path: Path) -> None:
        """A measured duration of 0.0 raises VideoValidationError."""
        video_path = _make_mp4(tmp_path)
        probe = _FakeDurationProbe(duration_seconds=0.0)
        validator = VideoValidator(duration_probe=probe)

        with pytest.raises(VideoValidationError, match="not positive"):
            validator.validate(video_path, expected_duration_seconds=10.0)

    def test_negative_duration_raises_video_validation_error(self, tmp_path: Path) -> None:
        """A negative measured duration raises VideoValidationError."""
        video_path = _make_mp4(tmp_path)
        probe = _FakeDurationProbe(duration_seconds=-1.0)
        validator = VideoValidator(duration_probe=probe)

        with pytest.raises(VideoValidationError, match="not positive"):
            validator.validate(video_path, expected_duration_seconds=10.0)


class TestToleranceBoundary:
    """Tests for the exact tolerance boundary."""

    def test_difference_exactly_at_tolerance_passes(self, tmp_path: Path) -> None:
        """A difference exactly equal to the tolerance is accepted."""
        video_path = _make_mp4(tmp_path)
        probe = _FakeDurationProbe(duration_seconds=10.5)
        validator = VideoValidator(duration_probe=probe, tolerance_seconds=0.5)

        result = validator.validate(video_path, expected_duration_seconds=10.0)

        assert result.is_valid is True

    def test_difference_just_beyond_tolerance_fails(self, tmp_path: Path) -> None:
        """A difference just beyond the tolerance is rejected."""
        video_path = _make_mp4(tmp_path)
        probe = _FakeDurationProbe(duration_seconds=10.51)
        validator = VideoValidator(duration_probe=probe, tolerance_seconds=0.5)

        with pytest.raises(VideoValidationError, match="differs from expected"):
            validator.validate(video_path, expected_duration_seconds=10.0)

    def test_per_call_tolerance_override(self, tmp_path: Path) -> None:
        """A per-call tolerance_seconds overrides the constructor default."""
        video_path = _make_mp4(tmp_path)
        probe = _FakeDurationProbe(duration_seconds=12.0)
        validator = VideoValidator(duration_probe=probe, tolerance_seconds=0.5)

        result = validator.validate(
            video_path, expected_duration_seconds=10.0, tolerance_seconds=5.0
        )

        assert result.is_valid is True


class TestMultipleFailuresCollectedTogether:
    """Tests verifying all failing checks are collected into one exception."""

    def test_four_simultaneous_failures_all_reported_together(
        self, tmp_path: Path
    ) -> None:
        """Wrong extension, empty file, non-positive duration, and duration
        mismatch are all reported in a single raised VideoValidationError,
        rather than stopping at the first failure.
        """
        video_path = _make_mp4(tmp_path, name="final.mkv", size_bytes=0)
        probe = _FakeDurationProbe(duration_seconds=-3.0)
        validator = VideoValidator(duration_probe=probe, tolerance_seconds=0.5)

        with pytest.raises(VideoValidationError) as exc_info:
            validator.validate(video_path, expected_duration_seconds=10.0)

        message = str(exc_info.value)
        assert "extension" in message
        assert "empty" in message
        assert "not positive" in message
        assert "differs from expected" in message

    def test_probe_failure_still_reports_other_check_failures(
        self, tmp_path: Path
    ) -> None:
        """A probe failure alongside other failing checks reports both."""
        video_path = _make_mp4(tmp_path, name="final.mkv", size_bytes=0)
        probe = _FakeDurationProbe(error=RuntimeError("ffprobe crashed"))
        validator = VideoValidator(duration_probe=probe)

        with pytest.raises(VideoValidationError) as exc_info:
            validator.validate(video_path, expected_duration_seconds=10.0)

        message = str(exc_info.value)
        assert "extension" in message
        assert "empty" in message
        assert "Failed to probe" in message


class TestProbeFailure:
    """Tests for the injected duration probe raising an error."""

    def test_probe_exception_raises_video_validation_error(self, tmp_path: Path) -> None:
        """An exception from the duration probe is wrapped in VideoValidationError."""
        video_path = _make_mp4(tmp_path)
        probe = _FakeDurationProbe(error=RuntimeError("ffprobe crashed"))
        validator = VideoValidator(duration_probe=probe)

        with pytest.raises(VideoValidationError, match="Failed to probe"):
            validator.validate(video_path, expected_duration_seconds=10.0)



class TestNoSideEffects:
    """Tests verifying the validator never creates or modifies files."""

    def test_validate_does_not_create_new_files(self, tmp_path: Path) -> None:
        """Validating a video does not create any new files on disk."""
        video_path = _make_mp4(tmp_path)
        files_before = set(tmp_path.iterdir())
        probe = _FakeDurationProbe(duration_seconds=10.0)
        validator = VideoValidator(duration_probe=probe)

        validator.validate(video_path, expected_duration_seconds=10.0)

        files_after = set(tmp_path.iterdir())
        assert files_before == files_after
