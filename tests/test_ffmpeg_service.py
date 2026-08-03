"""Unit tests for the FFmpeg wrapper service (Component 4).

Scope is intentionally limited to
:class:`app.services.ffmpeg_service.FFmpegService`. No real ``ffmpeg``
or ``ffprobe`` process is ever executed - all process execution is
delegated to an injected fake :class:`SubprocessRunner`.

Executable-existence checks use real filesystem lookups
(:func:`shutil.which`), so tests that need the "executable exists"
check to pass use a stand-in executable name that genuinely exists on
this system (e.g. ``"python3"``), while process *behavior* is always
controlled by the injected fake runner - never a real invocation of
that executable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.exceptions import FFmpegError
from app.models.video import SubtitleCue
from app.services.ffmpeg_service import (
    FFmpegService,
    ProcessResult,
    RealSubprocessRunner,
    SubprocessRunner,
)

#: A stand-in executable name guaranteed to exist on this system,
#: used only to satisfy the real `shutil.which` existence check.
#: Actual process behavior is always controlled by the fake runner.
_EXISTING_EXECUTABLE = "python3"
_MISSING_EXECUTABLE = "definitely-not-a-real-executable-xyz"


class _FakeSubprocessRunner:
    """A fake SubprocessRunner returning a configured, canned result."""

    def __init__(
        self,
        return_code: int = 0,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
        self.commands: list[list[str]] = []

    def run(self, command: list[str]) -> ProcessResult:
        self.commands.append(list(command))
        return ProcessResult(
            return_code=self.return_code, stdout=self.stdout, stderr=self.stderr
        )


def _make_cue(text: str = "Hello world.") -> SubtitleCue:
    return SubtitleCue(index=0, start_seconds=0.0, end_seconds=5.0, text=text)


class TestSubprocessRunnerProtocol:
    """Tests verifying the SubprocessRunner Protocol contract."""

    def test_fake_runner_satisfies_protocol(self) -> None:
        """The fake test double structurally satisfies SubprocessRunner."""
        runner: SubprocessRunner = _FakeSubprocessRunner()

        assert isinstance(runner, SubprocessRunner)

    def test_real_runner_satisfies_protocol(self) -> None:
        """RealSubprocessRunner structurally satisfies SubprocessRunner."""
        runner: SubprocessRunner = RealSubprocessRunner()

        assert isinstance(runner, SubprocessRunner)


class TestProbeDurationSuccess:
    """Tests for successful probe_duration() calls."""

    def test_returns_parsed_duration(self, tmp_path: Path) -> None:
        """A well-formed ffprobe stdout value is parsed into a float."""
        audio_path = tmp_path / "segment.mp3"
        audio_path.write_bytes(b"fake-audio")
        runner = _FakeSubprocessRunner(return_code=0, stdout="12.345\n")
        service = FFmpegService(
            runner=runner, ffprobe_executable=_EXISTING_EXECUTABLE
        )

        duration = service.probe_duration(audio_path)

        assert duration == pytest.approx(12.345)

    def test_invokes_runner_with_ffprobe_command(self, tmp_path: Path) -> None:
        """probe_duration passes a command referencing the audio path."""
        audio_path = tmp_path / "segment.mp3"
        audio_path.write_bytes(b"fake-audio")
        runner = _FakeSubprocessRunner(return_code=0, stdout="3.0")
        service = FFmpegService(
            runner=runner, ffprobe_executable=_EXISTING_EXECUTABLE
        )

        service.probe_duration(audio_path)

        assert len(runner.commands) == 1
        assert str(audio_path) in runner.commands[0]


class TestProbeDurationFailures:
    """Tests for probe_duration() failure paths."""

    def test_missing_executable_raises_ffmpeg_error(self, tmp_path: Path) -> None:
        """A non-existent ffprobe executable raises FFmpegError."""
        audio_path = tmp_path / "segment.mp3"
        audio_path.write_bytes(b"fake-audio")
        service = FFmpegService(
            runner=_FakeSubprocessRunner(),
            ffprobe_executable=_MISSING_EXECUTABLE,
        )

        with pytest.raises(FFmpegError, match="not found on PATH"):
            service.probe_duration(audio_path)

    def test_missing_input_file_raises_ffmpeg_error(self, tmp_path: Path) -> None:
        """A non-existent audio file raises FFmpegError before running ffprobe."""
        missing_audio = tmp_path / "does_not_exist.mp3"
        service = FFmpegService(
            runner=_FakeSubprocessRunner(), ffprobe_executable=_EXISTING_EXECUTABLE
        )

        with pytest.raises(FFmpegError, match="not found"):
            service.probe_duration(missing_audio)

    def test_nonzero_return_code_raises_ffmpeg_error(self, tmp_path: Path) -> None:
        """A non-zero ffprobe return code raises FFmpegError with stderr."""
        audio_path = tmp_path / "segment.mp3"
        audio_path.write_bytes(b"fake-audio")
        runner = _FakeSubprocessRunner(
            return_code=1, stderr="Invalid data found when processing input"
        )
        service = FFmpegService(
            runner=runner, ffprobe_executable=_EXISTING_EXECUTABLE
        )

        with pytest.raises(FFmpegError, match="Invalid data found"):
            service.probe_duration(audio_path)

    def test_unparseable_output_raises_ffmpeg_error(self, tmp_path: Path) -> None:
        """Non-numeric ffprobe stdout raises FFmpegError."""
        audio_path = tmp_path / "segment.mp3"
        audio_path.write_bytes(b"fake-audio")
        runner = _FakeSubprocessRunner(return_code=0, stdout="not-a-number")
        service = FFmpegService(
            runner=runner, ffprobe_executable=_EXISTING_EXECUTABLE
        )

        with pytest.raises(FFmpegError, match="Could not parse duration"):
            service.probe_duration(audio_path)


class TestRenderSegmentSuccess:
    """Tests for successful render_segment() calls."""

    def test_returns_output_path(self, tmp_path: Path) -> None:
        """A successful render returns the given output_path."""
        audio_path = tmp_path / "audio.mp3"
        image_path = tmp_path / "image.png"
        audio_path.write_bytes(b"fake-audio")
        image_path.write_bytes(b"fake-image")
        output_path = tmp_path / "clip.mp4"
        service = FFmpegService(
            runner=_FakeSubprocessRunner(return_code=0),
            ffmpeg_executable=_EXISTING_EXECUTABLE,
        )

        result = service.render_segment(
            audio_path, image_path, _make_cue(), output_path
        )

        assert result == output_path

    def test_creates_output_parent_directory(self, tmp_path: Path) -> None:
        """render_segment creates missing parent directories for output_path."""
        audio_path = tmp_path / "audio.mp3"
        image_path = tmp_path / "image.png"
        audio_path.write_bytes(b"fake-audio")
        image_path.write_bytes(b"fake-image")
        output_path = tmp_path / "nested" / "clip.mp4"
        service = FFmpegService(
            runner=_FakeSubprocessRunner(return_code=0),
            ffmpeg_executable=_EXISTING_EXECUTABLE,
        )

        service.render_segment(audio_path, image_path, _make_cue(), output_path)

        assert output_path.parent.exists()

    def test_command_references_audio_and_image_paths(self, tmp_path: Path) -> None:
        """The generated ffmpeg command references both input paths."""
        audio_path = tmp_path / "audio.mp3"
        image_path = tmp_path / "image.png"
        audio_path.write_bytes(b"fake-audio")
        image_path.write_bytes(b"fake-image")
        output_path = tmp_path / "clip.mp4"
        runner = _FakeSubprocessRunner(return_code=0)
        service = FFmpegService(
            runner=runner, ffmpeg_executable=_EXISTING_EXECUTABLE
        )

        service.render_segment(audio_path, image_path, _make_cue(), output_path)

        command = runner.commands[0]
        assert str(audio_path) in command
        assert str(image_path) in command
        assert str(output_path) in command


class TestRenderSegmentFailures:
    """Tests for render_segment() failure paths."""

    def test_missing_executable_raises_ffmpeg_error(self, tmp_path: Path) -> None:
        """A non-existent ffmpeg executable raises FFmpegError."""
        audio_path = tmp_path / "audio.mp3"
        image_path = tmp_path / "image.png"
        audio_path.write_bytes(b"x")
        image_path.write_bytes(b"x")
        service = FFmpegService(
            runner=_FakeSubprocessRunner(), ffmpeg_executable=_MISSING_EXECUTABLE
        )

        with pytest.raises(FFmpegError, match="not found on PATH"):
            service.render_segment(
                audio_path, image_path, _make_cue(), tmp_path / "clip.mp4"
            )

    def test_missing_audio_input_raises_ffmpeg_error(self, tmp_path: Path) -> None:
        """A missing audio file raises FFmpegError before invoking ffmpeg."""
        missing_audio = tmp_path / "missing.mp3"
        image_path = tmp_path / "image.png"
        image_path.write_bytes(b"x")
        service = FFmpegService(
            runner=_FakeSubprocessRunner(), ffmpeg_executable=_EXISTING_EXECUTABLE
        )

        with pytest.raises(FFmpegError, match="not found"):
            service.render_segment(
                missing_audio, image_path, _make_cue(), tmp_path / "clip.mp4"
            )

    def test_missing_image_input_raises_ffmpeg_error(self, tmp_path: Path) -> None:
        """A missing image file raises FFmpegError before invoking ffmpeg."""
        audio_path = tmp_path / "audio.mp3"
        audio_path.write_bytes(b"x")
        missing_image = tmp_path / "missing.png"
        service = FFmpegService(
            runner=_FakeSubprocessRunner(), ffmpeg_executable=_EXISTING_EXECUTABLE
        )

        with pytest.raises(FFmpegError, match="not found"):
            service.render_segment(
                audio_path, missing_image, _make_cue(), tmp_path / "clip.mp4"
            )

    def test_nonzero_return_code_raises_ffmpeg_error(self, tmp_path: Path) -> None:
        """A failed ffmpeg process (non-zero return code) raises FFmpegError."""
        audio_path = tmp_path / "audio.mp3"
        image_path = tmp_path / "image.png"
        audio_path.write_bytes(b"x")
        image_path.write_bytes(b"x")
        runner = _FakeSubprocessRunner(return_code=1, stderr="encoder not found")
        service = FFmpegService(
            runner=runner, ffmpeg_executable=_EXISTING_EXECUTABLE
        )

        with pytest.raises(FFmpegError, match="encoder not found"):
            service.render_segment(
                audio_path, image_path, _make_cue(), tmp_path / "clip.mp4"
            )


class TestConcatenateSegmentsSuccess:
    """Tests for successful concatenate_segments() calls."""

    def test_returns_output_path(self, tmp_path: Path) -> None:
        """A successful concatenation returns the given output_path."""
        clip_a = tmp_path / "00_intro.mp4"
        clip_b = tmp_path / "01_history.mp4"
        clip_a.write_bytes(b"x")
        clip_b.write_bytes(b"x")
        output_path = tmp_path / "final.mp4"
        service = FFmpegService(
            runner=_FakeSubprocessRunner(return_code=0),
            ffmpeg_executable=_EXISTING_EXECUTABLE,
        )

        result = service.concatenate_segments((clip_a, clip_b), output_path)

        assert result == output_path

    def test_command_references_output_path(self, tmp_path: Path) -> None:
        """The generated ffmpeg command references the final output path."""
        clip_a = tmp_path / "00_intro.mp4"
        clip_a.write_bytes(b"x")
        output_path = tmp_path / "final.mp4"
        runner = _FakeSubprocessRunner(return_code=0)
        service = FFmpegService(
            runner=runner, ffmpeg_executable=_EXISTING_EXECUTABLE
        )

        service.concatenate_segments((clip_a,), output_path)

        assert str(output_path) in runner.commands[0]

    def test_concat_list_file_is_cleaned_up(self, tmp_path: Path) -> None:
        """The temporary concat list file does not persist after the call."""
        clip_a = tmp_path / "00_intro.mp4"
        clip_a.write_bytes(b"x")
        output_path = tmp_path / "final.mp4"
        runner = _FakeSubprocessRunner(return_code=0)
        service = FFmpegService(
            runner=runner, ffmpeg_executable=_EXISTING_EXECUTABLE
        )

        service.concatenate_segments((clip_a,), output_path)

        list_file_path = Path(runner.commands[0][runner.commands[0].index("-i") + 1])
        assert not list_file_path.exists()


class TestConcatenateSegmentsFailures:
    """Tests for concatenate_segments() failure paths."""

    def test_missing_executable_raises_ffmpeg_error(self, tmp_path: Path) -> None:
        """A non-existent ffmpeg executable raises FFmpegError."""
        clip_a = tmp_path / "00_intro.mp4"
        clip_a.write_bytes(b"x")
        service = FFmpegService(
            runner=_FakeSubprocessRunner(), ffmpeg_executable=_MISSING_EXECUTABLE
        )

        with pytest.raises(FFmpegError, match="not found on PATH"):
            service.concatenate_segments((clip_a,), tmp_path / "final.mp4")

    def test_missing_segment_file_raises_ffmpeg_error(self, tmp_path: Path) -> None:
        """A missing segment clip raises FFmpegError before invoking ffmpeg."""
        clip_a = tmp_path / "00_intro.mp4"
        clip_a.write_bytes(b"x")
        missing_clip = tmp_path / "01_missing.mp4"
        service = FFmpegService(
            runner=_FakeSubprocessRunner(), ffmpeg_executable=_EXISTING_EXECUTABLE
        )

        with pytest.raises(FFmpegError, match="not found"):
            service.concatenate_segments(
                (clip_a, missing_clip), tmp_path / "final.mp4"
            )

    def test_nonzero_return_code_raises_ffmpeg_error(self, tmp_path: Path) -> None:
        """A failed ffmpeg process (non-zero return code) raises FFmpegError."""
        clip_a = tmp_path / "00_intro.mp4"
        clip_a.write_bytes(b"x")
        runner = _FakeSubprocessRunner(return_code=1, stderr="concat failed")
        service = FFmpegService(
            runner=runner, ffmpeg_executable=_EXISTING_EXECUTABLE
        )

        with pytest.raises(FFmpegError, match="concat failed"):
            service.concatenate_segments((clip_a,), tmp_path / "final.mp4")

    def test_concat_list_file_cleaned_up_even_on_failure(self, tmp_path: Path) -> None:
        """The temporary list file is removed even when ffmpeg fails."""
        clip_a = tmp_path / "00_intro.mp4"
        clip_a.write_bytes(b"x")
        runner = _FakeSubprocessRunner(return_code=1, stderr="boom")
        service = FFmpegService(
            runner=runner, ffmpeg_executable=_EXISTING_EXECUTABLE
        )

        with pytest.raises(FFmpegError):
            service.concatenate_segments((clip_a,), tmp_path / "final.mp4")

        list_file_path = Path(runner.commands[0][runner.commands[0].index("-i") + 1])
        assert not list_file_path.exists()


class TestNoDirectSubprocessCallsInBusinessLogic:
    """Tests verifying subprocess execution is fully delegated."""

    def test_service_only_invokes_the_injected_runner(self, tmp_path: Path) -> None:
        """Passing a fake runner means it is the only one ever invoked."""
        audio_path = tmp_path / "audio.mp3"
        audio_path.write_bytes(b"x")
        runner = _FakeSubprocessRunner(return_code=0, stdout="1.0")
        service = FFmpegService(
            runner=runner, ffprobe_executable=_EXISTING_EXECUTABLE
        )

        service.probe_duration(audio_path)

        assert len(runner.commands) == 1
