"""FFmpeg wrapper service.

This module wraps the ``ffmpeg``/``ffprobe`` command-line tools only.
It performs no orchestration, no subtitle timing computation, no
image lookup, and no filename generation, and it never invokes
``subprocess.run()`` directly inside its business logic - all process
execution is delegated to an injected :class:`SubprocessRunner`,
following the same Dependency Inversion pattern used for
:class:`~app.services.tts_service.TTSEngine` in Milestone 3.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.exceptions import FFmpegError
from app.models.video import SubtitleCue


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """The outcome of running an external command.

    Attributes:
        return_code: The process's exit code. ``0`` conventionally
            indicates success.
        stdout: Captured standard output text.
        stderr: Captured standard error text.
    """

    return_code: int
    stdout: str
    stderr: str


@runtime_checkable
class SubprocessRunner(Protocol):
    """Abstraction for executing an external command.

    Any class implementing this protocol can be injected into
    :class:`FFmpegService`, regardless of whether it runs a real
    process or returns a canned result for testing.
    """

    def run(self, command: Sequence[str]) -> ProcessResult:
        """Execute a command and return its result.

        Args:
            command: The command and its arguments, as a sequence of
                strings (no shell interpretation).

        Returns:
            A :class:`ProcessResult` describing the outcome.
        """
        ...


class RealSubprocessRunner:
    """The default :class:`SubprocessRunner`: runs a real OS process."""

    def run(self, command: Sequence[str]) -> ProcessResult:
        """Execute the given command as a real subprocess.

        Args:
            command: The command and its arguments.

        Returns:
            A :class:`ProcessResult` with the real process's exit
            code, stdout, and stderr.
        """
        completed = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            check=False,
        )
        return ProcessResult(
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


class FFmpegService:
    """A thin wrapper around the ``ffmpeg`` and ``ffprobe`` executables.

    All process execution is delegated to an injected
    :class:`SubprocessRunner`, and all executable resolution uses
    :func:`shutil.which` (a filesystem check, not a subprocess call),
    so this class can be fully exercised in tests with no real FFmpeg
    installation and no real process execution.
    """

    def __init__(
        self,
        runner: SubprocessRunner | None = None,
        ffmpeg_executable: str = "ffmpeg",
        ffprobe_executable: str = "ffprobe",
    ) -> None:
        """Initialize the service.

        Args:
            runner: An injected :class:`SubprocessRunner` used to
                execute all commands. Defaults to
                :class:`RealSubprocessRunner`, which runs real OS
                processes.
            ffmpeg_executable: The name or path of the ffmpeg
                executable to invoke. Defaults to ``"ffmpeg"``
                (resolved via the system ``PATH``).
            ffprobe_executable: The name or path of the ffprobe
                executable to invoke. Defaults to ``"ffprobe"``
                (resolved via the system ``PATH``).
        """
        self._runner = runner if runner is not None else RealSubprocessRunner()
        self._ffmpeg_executable = ffmpeg_executable
        self._ffprobe_executable = ffprobe_executable

    def probe_duration(self, audio_path: Path) -> float:
        """Measure the duration of an audio file, in seconds.

        Args:
            audio_path: Path to the audio file to measure.

        Returns:
            The audio file's duration, in seconds.

        Raises:
            FFmpegError: If ``ffprobe`` is not found on the system
                PATH, if ``audio_path`` does not exist, if the
                underlying process exits with a non-zero return code,
                or if its output cannot be parsed as a duration.
        """
        self._require_executable(self._ffprobe_executable)
        self._require_file_exists(audio_path)

        command = [
            self._ffprobe_executable,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrapper=1:nokey=1",
            str(audio_path),
        ]
        result = self._runner.run(command)

        if result.return_code != 0:
            raise FFmpegError(
                f"ffprobe failed for '{audio_path}' (exit code "
                f"{result.return_code}): {result.stderr.strip()}"
            )

        try:
            return float(result.stdout.strip())
        except ValueError as exc:
            raise FFmpegError(
                f"Could not parse duration from ffprobe output for "
                f"'{audio_path}': {result.stdout!r}"
            ) from exc

    def render_segment(
        self,
        audio_path: Path,
        image_path: Path,
        subtitle: SubtitleCue,
        output_path: Path,
    ) -> Path:
        """Render one video segment from a still image, audio, and subtitle text.

        Args:
            audio_path: Path to the segment's narrated audio file.
            image_path: Path to the still image to display for the
                segment's duration.
            subtitle: The subtitle cue whose text should be burned
                into the rendered clip.
            output_path: Path the rendered video clip should be
                written to. Parent directories are created if needed.

        Returns:
            ``output_path``, once the clip has been successfully
            rendered.

        Raises:
            FFmpegError: If ``ffmpeg`` is not found on the system
                PATH, if ``audio_path`` or ``image_path`` does not
                exist, or if the underlying process exits with a
                non-zero return code.
        """
        self._require_executable(self._ffmpeg_executable)
        self._require_file_exists(audio_path)
        self._require_file_exists(image_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        escaped_text = subtitle.text.replace("'", r"\'").replace(":", r"\:")
        drawtext_filter = (
            f"drawtext=text='{escaped_text}':fontcolor=white:fontsize=24:"
            "x=(w-text_w)/2:y=h-th-40:box=1:boxcolor=black@0.5:boxborderw=8"
        )

        command = [
            self._ffmpeg_executable,
            "-y",
            "-loop",
            "1",
            "-i",
            str(image_path),
            "-i",
            str(audio_path),
            "-vf",
            drawtext_filter,
            "-c:v",
            "libx264",
            "-tune",
            "stillimage",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-pix_fmt",
            "yuv420p",
            "-shortest",
            str(output_path),
        ]
        result = self._runner.run(command)

        if result.return_code != 0:
            raise FFmpegError(
                f"ffmpeg failed to render segment to '{output_path}' "
                f"(exit code {result.return_code}): {result.stderr.strip()}"
            )

        return output_path

    def concatenate_segments(
        self,
        segment_paths: tuple[Path, ...],
        output_path: Path,
    ) -> Path:
        """Concatenate multiple rendered video clips into one final video.

        Args:
            segment_paths: An ordered tuple of paths to the rendered
                segment clips to concatenate, in final video order.
            output_path: Path the concatenated video should be written
                to. Parent directories are created if needed.

        Returns:
            ``output_path``, once concatenation has succeeded.

        Raises:
            FFmpegError: If ``ffmpeg`` is not found on the system
                PATH, if any path in ``segment_paths`` does not exist,
                or if the underlying process exits with a non-zero
                return code.
        """
        self._require_executable(self._ffmpeg_executable)
        for segment_path in segment_paths:
            self._require_file_exists(segment_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        concat_list_path = self._write_concat_list(segment_paths)
        try:
            command = [
                self._ffmpeg_executable,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list_path),
                "-c",
                "copy",
                str(output_path),
            ]
            result = self._runner.run(command)
        finally:
            concat_list_path.unlink(missing_ok=True)

        if result.return_code != 0:
            raise FFmpegError(
                f"ffmpeg failed to concatenate segments into "
                f"'{output_path}' (exit code {result.return_code}): "
                f"{result.stderr.strip()}"
            )

        return output_path

    def _require_executable(self, executable: str) -> None:
        """Validate that a required executable is available on PATH.

        Args:
            executable: The executable name or path to check.

        Raises:
            FFmpegError: If the executable cannot be resolved.
        """
        if shutil.which(executable) is None:
            raise FFmpegError(
                f"Required executable not found on PATH: '{executable}'"
            )

    def _require_file_exists(self, path: Path) -> None:
        """Validate that an input file exists.

        Args:
            path: The file path to check.

        Raises:
            FFmpegError: If the path does not exist or is not a file.
        """
        if not path.is_file():
            raise FFmpegError(f"Required input file not found: '{path}'")

    def _write_concat_list(self, segment_paths: tuple[Path, ...]) -> Path:
        """Write a temporary FFmpeg concat-demuxer list file.

        Args:
            segment_paths: Paths to include, in order.

        Returns:
            Path to the written temporary list file. The caller is
            responsible for deleting it once finished.
        """
        descriptor, list_path_str = tempfile.mkstemp(suffix=".txt", text=True)
        list_path = Path(list_path_str)
        with open(descriptor, "w", encoding="utf-8") as list_file:
            for segment_path in segment_paths:
                escaped_path = str(segment_path).replace("'", r"'\''")
                list_file.write(f"file '{escaped_path}'\n")
        return list_path
