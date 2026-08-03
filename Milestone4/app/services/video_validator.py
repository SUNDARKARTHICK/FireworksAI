"""Video validation service.

This module validates an already-rendered video file: existence,
extension, non-emptiness, and duration correctness. It performs no
rendering, no FFmpeg invocation of its own, no image lookup, no
subtitle timing, and no pipeline orchestration, and it creates or
modifies no files.

Duration measurement is delegated to an injected
:class:`DurationProbe`-shaped object (e.g. a
:class:`~app.services.ffmpeg_service.FFmpegService` instance), never
constructed internally - this module does not import
:mod:`app.services.ffmpeg_service` at all.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from app.exceptions import VideoValidationError
from app.models.video import VideoValidationResult

_EXPECTED_EXTENSION = ".mp4"
_DEFAULT_TOLERANCE_SECONDS = 0.5


@runtime_checkable
class DurationProbe(Protocol):
    """Abstraction for measuring a media file's duration.

    Any object exposing this method (e.g.
    :class:`~app.services.ffmpeg_service.FFmpegService`) can be
    injected into :class:`VideoValidator`, regardless of how it
    actually measures duration.
    """

    def probe_duration(self, path: Path) -> float:
        """Measure the duration of a media file, in seconds.

        Args:
            path: Path to the media file to measure.

        Returns:
            The file's duration, in seconds.
        """
        ...


class VideoValidator:
    """Validates a rendered video file against expected properties.

    All duration measurement is delegated to an injected
    :class:`DurationProbe`; this class never measures duration itself
    and never constructs a concrete prober.
    """

    def __init__(
        self,
        duration_probe: DurationProbe,
        tolerance_seconds: float = _DEFAULT_TOLERANCE_SECONDS,
    ) -> None:
        """Initialize the validator.

        Args:
            duration_probe: An injected object used to measure the
                video's actual duration.
            tolerance_seconds: The default allowed difference, in
                seconds, between a video's measured duration and its
                expected duration for the video to be considered
                valid. Can be overridden per call to :meth:`validate`.
        """
        self._duration_probe = duration_probe
        self._tolerance_seconds = tolerance_seconds

    def validate(
        self,
        video_path: Path,
        expected_duration_seconds: float,
        tolerance_seconds: float | None = None,
    ) -> VideoValidationResult:
        """Validate a rendered video file.

        Args:
            video_path: Path to the rendered video file to validate.
            expected_duration_seconds: The duration, in seconds, the
                video is expected to have.
            tolerance_seconds: The allowed difference, in seconds,
                between measured and expected duration. Defaults to
                the tolerance configured at construction time when
                not provided.

        Returns:
            A :class:`~app.models.video.VideoValidationResult` with
            ``is_valid=True`` if every check passes.

        Raises:
            VideoValidationError: If ``video_path`` does not exist, or
                if any combination of the extension, non-empty,
                positive-duration, or duration-matches-expected checks
                fails. The error message lists every failing check.
        """
        effective_tolerance = (
            tolerance_seconds if tolerance_seconds is not None else self._tolerance_seconds
        )

        if not video_path.is_file():
            raise VideoValidationError(f"Video file not found: '{video_path}'")

        checks_performed: list[str] = ["file_exists"]
        errors: list[str] = []

        checks_performed.append("extension")
        if video_path.suffix.lower() != _EXPECTED_EXTENSION:
            errors.append(
                f"Unsupported file extension '{video_path.suffix}'; "
                f"expected '{_EXPECTED_EXTENSION}'."
            )

        checks_performed.append("non_empty")
        if video_path.stat().st_size <= 0:
            errors.append(f"Video file is empty: '{video_path}'")

        measured_duration: float | None = None
        checks_performed.append("duration_probe")
        try:
            measured_duration = self._duration_probe.probe_duration(video_path)
        except Exception as exc:  # noqa: BLE001 - any probe failure is a validation error
            errors.append(f"Failed to probe video duration: {exc}")

        if measured_duration is not None:
            checks_performed.append("duration_positive")
            if measured_duration <= 0:
                errors.append(
                    f"Measured duration is not positive: {measured_duration}"
                )

            checks_performed.append("duration_matches_expected")
            difference = abs(measured_duration - expected_duration_seconds)
            if difference > effective_tolerance:
                errors.append(
                    f"Measured duration {measured_duration:.3f}s differs "
                    f"from expected {expected_duration_seconds:.3f}s by "
                    f"{difference:.3f}s, exceeding tolerance of "
                    f"{effective_tolerance:.3f}s."
                )

        if errors:
            raise VideoValidationError(
                f"Video validation failed for '{video_path}': " + "; ".join(errors)
            )

        return VideoValidationResult(
            video_path=video_path,
            is_valid=True,
            duration_seconds=measured_duration,
            checks_performed=tuple(checks_performed),
            errors=(),
        )
