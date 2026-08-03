"""Unit tests for the video assembly pipeline (Component 6).

Scope is intentionally limited to
:class:`app.pipeline.video_pipeline.VideoPipeline`. No real FFmpeg, no
subprocess, no real media rendering, and no network access occur
anywhere in this file - every dependency is a fake/mock injected via
the constructor.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings
from app.exceptions import (
    FFmpegError,
    ImageLoadError,
    SubtitleTimingError,
    VideoValidationError,
)
from app.models.audio import AudioGenerationResult, AudioSegment, NarrationSegment
from app.models.script import Metadata, Script, Section
from app.models.video import (
    ImageAsset,
    SubtitleCue,
    VideoAssemblyResult,
    VideoValidationResult,
)
from app.pipeline.video_pipeline import VideoPipeline


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeImageLoader:
    """A fake image_loader callable, recording calls and call order."""

    def __init__(
        self,
        call_log: list[str],
        error: Exception | None = None,
    ) -> None:
        self._call_log = call_log
        self._error = error
        self.calls: list[tuple[Path, tuple[NarrationSegment, ...]]] = []

    def __call__(
        self, image_dir: Path, segments: tuple[NarrationSegment, ...]
    ) -> tuple[ImageAsset, ...]:
        self._call_log.append("image_loader")
        self.calls.append((image_dir, segments))
        if self._error is not None:
            raise self._error
        return tuple(
            ImageAsset(index=segment.index, file_path=image_dir / f"{segment.index}.png")
            for segment in segments
        )


class _FakeSubtitleBuilder:
    """A fake subtitle_builder callable, recording calls and call order."""

    def __init__(
        self,
        call_log: list[str],
        error: Exception | None = None,
    ) -> None:
        self._call_log = call_log
        self._error = error
        self.calls: list[tuple[AudioSegment, ...]] = []

    def __call__(
        self, audio_segments: tuple[AudioSegment, ...]
    ) -> tuple[SubtitleCue, ...]:
        self._call_log.append("subtitle_builder")
        self.calls.append(audio_segments)
        if self._error is not None:
            raise self._error
        cues = []
        start = 0.0
        for audio_segment in audio_segments:
            end = start + (audio_segment.duration_seconds or 0.0)
            cues.append(
                SubtitleCue(
                    index=audio_segment.segment.index,
                    start_seconds=start,
                    end_seconds=end,
                    text=audio_segment.segment.text,
                )
            )
            start = end
        return tuple(cues)


class _FakeFFmpegService:
    """A fake FFmpeg service satisfying the VideoRenderer protocol."""

    def __init__(
        self,
        call_log: list[str],
        durations: dict[str, float] | None = None,
        probe_error: Exception | None = None,
        render_error: Exception | None = None,
        concatenate_error: Exception | None = None,
    ) -> None:
        self._call_log = call_log
        self._durations = durations or {}
        self._probe_error = probe_error
        self._render_error = render_error
        self._concatenate_error = concatenate_error
        self.probe_calls: list[Path] = []
        self.render_calls: list[tuple[Path, Path, SubtitleCue, Path]] = []
        self.concatenate_calls: list[tuple[tuple[Path, ...], Path]] = []

    def probe_duration(self, path: Path) -> float:
        self._call_log.append("probe_duration")
        self.probe_calls.append(path)
        if self._probe_error is not None:
            raise self._probe_error
        return self._durations.get(str(path), 2.0)

    def render_segment(
        self,
        audio_path: Path,
        image_path: Path,
        subtitle: SubtitleCue,
        output_path: Path,
    ) -> Path:
        self._call_log.append("render_segment")
        self.render_calls.append((audio_path, image_path, subtitle, output_path))
        if self._render_error is not None:
            raise self._render_error
        return output_path

    def concatenate_segments(
        self,
        segment_paths: tuple[Path, ...],
        output_path: Path,
    ) -> Path:
        self._call_log.append("concatenate_segments")
        self.concatenate_calls.append((segment_paths, output_path))
        if self._concatenate_error is not None:
            raise self._concatenate_error
        return output_path


class _FakeVideoValidator:
    """A fake video validator satisfying the Validator protocol."""

    def __init__(
        self,
        call_log: list[str],
        error: Exception | None = None,
    ) -> None:
        self._call_log = call_log
        self._error = error
        self.calls: list[tuple[Path, float]] = []

    def validate(
        self, video_path: Path, expected_duration_seconds: float
    ) -> VideoValidationResult:
        self._call_log.append("validate")
        self.calls.append((video_path, expected_duration_seconds))
        if self._error is not None:
            raise self._error
        return VideoValidationResult(
            video_path=video_path,
            is_valid=True,
            duration_seconds=expected_duration_seconds,
            checks_performed=("file_exists",),
            errors=(),
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_audio_result(num_segments: int = 2) -> AudioGenerationResult:
    """Build an AudioGenerationResult fixture with N narrated segments."""
    if num_segments <= 0:
        script = Script(
            metadata=Metadata(title="Test Lesson", author="Author", date="2026-07-30"),
            introduction="Intro text.",
            sections=(Section(heading="Topic", content="Content."),),
            conclusion="Conclusion text.",
        )
        return AudioGenerationResult(script=script, segments=())

    labels: list[str] = []
    if num_segments == 1:
        labels = ["introduction"]
    else:
        labels = ["introduction"]
        labels += [f"topic-{i}" for i in range(num_segments - 2)]
        labels += ["conclusion"]

    script = Script(
        metadata=Metadata(title="Test Lesson", author="Author", date="2026-07-30"),
        introduction="Intro text.",
        sections=tuple(
            Section(heading=f"Topic {i}", content=f"Content {i}.")
            for i in range(max(num_segments - 2, 1))
        ),
        conclusion="Conclusion text.",
    )

    segments = tuple(
        AudioSegment(
            segment=NarrationSegment(index=i, label=label, text=f"Text {i}."),
            file_path=Path(f"/fake/audio/{i:02d}_{label}.mp3"),
            duration_seconds=None,
        )
        for i, label in enumerate(labels)
    )
    return AudioGenerationResult(script=script, segments=segments)


def _make_settings(tmp_path: Path) -> Settings:
    # Construct Settings compatible with app.core.config.Settings
    return Settings(
        project_name="TestProject",
        app_env="test",
        log_level="INFO",
        output_dir=tmp_path / "output",
        assets_dir=tmp_path / "assets",
    )


def _make_pipeline(
    tmp_path: Path,
    call_log: list[str],
    durations: dict[str, float] | None = None,
    image_loader_error: Exception | None = None,
    subtitle_builder_error: Exception | None = None,
    probe_error: Exception | None = None,
    render_error: Exception | None = None,
    concatenate_error: Exception | None = None,
    validator_error: Exception | None = None,
) -> tuple[VideoPipeline, dict[str, object]]:
    settings = _make_settings(tmp_path)
    image_loader = _FakeImageLoader(call_log, error=image_loader_error)
    subtitle_builder = _FakeSubtitleBuilder(call_log, error=subtitle_builder_error)
    ffmpeg_service = _FakeFFmpegService(
        call_log,
        durations=durations,
        probe_error=probe_error,
        render_error=render_error,
        concatenate_error=concatenate_error,
    )
    video_validator = _FakeVideoValidator(call_log, error=validator_error)

    pipeline = VideoPipeline(
        image_loader=image_loader,
        subtitle_builder=subtitle_builder,
        ffmpeg_service=ffmpeg_service,
        video_validator=video_validator,
        settings=settings,
    )
    fakes = {
        "settings": settings,
        "image_loader": image_loader,
        "subtitle_builder": subtitle_builder,
        "ffmpeg_service": ffmpeg_service,
        "video_validator": video_validator,
    }
    return pipeline, fakes


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSuccessfulPipeline:
    """Tests for the fully successful assembly path."""

    def test_returns_video_assembly_result(self, tmp_path: Path) -> None:
        """A successful run returns a VideoAssemblyResult."""
        call_log: list[str] = []
        pipeline, _ = _make_pipeline(tmp_path, call_log)
        audio_result = _make_audio_result(num_segments=2)

        result = pipeline.assemble_video(audio_result)

        assert isinstance(result, VideoAssemblyResult)

    def test_result_references_source_script(self, tmp_path: Path) -> None:
        """The result's script matches the source AudioGenerationResult's script."""
        call_log: list[str] = []
        pipeline, _ = _make_pipeline(tmp_path, call_log)
        audio_result = _make_audio_result(num_segments=2)

        result = pipeline.assemble_video(audio_result)

        assert result.script is audio_result.script

    def test_result_output_path_under_settings_output_dir(self, tmp_path: Path) -> None:
        """The final output path is written under settings.output_dir."""
        call_log: list[str] = []
        pipeline, fakes = _make_pipeline(tmp_path, call_log)
        audio_result = _make_audio_result(num_segments=2)

        result = pipeline.assemble_video(audio_result)

        assert result.output_path == fakes["settings"].output_dir / "final.mp4"

    def test_custom_output_filename_is_respected(self, tmp_path: Path) -> None:
        """A custom output_filename is used for the final video path."""
        call_log: list[str] = []
        pipeline, fakes = _make_pipeline(tmp_path, call_log)
        audio_result = _make_audio_result(num_segments=1)

        result = pipeline.assemble_video(audio_result, output_filename="custom.mp4")

        assert result.output_path == fakes["settings"].output_dir / "custom.mp4"


class TestCorrectVideoAssemblyResult:
    """Tests verifying the returned result's content is fully correct."""

    def test_total_duration_is_sum_of_segment_durations(self, tmp_path: Path) -> None:
        """total_duration_seconds equals the sum of all probed durations."""
        call_log: list[str] = []
        audio_result = _make_audio_result(num_segments=3)
        durations = {
            str(segment.file_path): float(3 + i)
            for i, segment in enumerate(audio_result.segments)
        }
        pipeline, _ = _make_pipeline(tmp_path, call_log, durations=durations)

        result = pipeline.assemble_video(audio_result)

        assert result.total_duration_seconds == pytest.approx(sum(durations.values()))

    def test_segments_match_source_segment_count_and_order(self, tmp_path: Path) -> None:
        """Result segments preserve count and index/label order."""
        call_log: list[str] = []
        audio_result = _make_audio_result(num_segments=3)
        pipeline, _ = _make_pipeline(tmp_path, call_log)

        result = pipeline.assemble_video(audio_result)

        assert len(result.segments) == 3
        assert [plan.index for plan in result.segments] == [0, 1, 2]
        assert [plan.label for plan in result.segments] == [
            audio_segment.segment.label for audio_segment in audio_result.segments
        ]

    def test_segment_plans_reference_correct_audio_and_image_paths(
        self, tmp_path: Path
    ) -> None:
        """Each VideoSegmentPlan references the correct audio and image paths."""
        call_log: list[str] = []
        audio_result = _make_audio_result(num_segments=1)
        pipeline, fakes = _make_pipeline(tmp_path, call_log)

        result = pipeline.assemble_video(audio_result)

        plan = result.segments[0]
        assert plan.audio_path == audio_result.segments[0].file_path
        assert plan.image_path == fakes["image_loader"].calls[0][0] / "0.png"


class TestDependencyCallOrder:
    """Tests verifying the pipeline calls dependencies in the correct order."""

    def test_call_order_matches_specified_pipeline_flow(self, tmp_path: Path) -> None:
        """image_loader -> probe_duration(s) -> subtitle_builder -> render(s) -> concatenate -> validate."""
        call_log: list[str] = []
        audio_result = _make_audio_result(num_segments=2)
        pipeline, _ = _make_pipeline(tmp_path, call_log)

        pipeline.assemble_video(audio_result)

        image_loader_index = call_log.index("image_loader")
        first_probe_index = call_log.index("probe_duration")
        subtitle_builder_index = call_log.index("subtitle_builder")
        first_render_index = call_log.index("render_segment")
        concatenate_index = call_log.index("concatenate_segments")
        validate_index = call_log.index("validate")

        assert image_loader_index < first_probe_index
        assert first_probe_index < subtitle_builder_index
        assert subtitle_builder_index < first_render_index
        assert first_render_index < concatenate_index
        assert concatenate_index < validate_index

    def test_probe_duration_called_once_per_segment(self, tmp_path: Path) -> None:
        """probe_duration is invoked exactly once per audio segment."""
        call_log: list[str] = []
        audio_result = _make_audio_result(num_segments=3)
        pipeline, _ = _make_pipeline(tmp_path, call_log)

        pipeline.assemble_video(audio_result)

        assert call_log.count("probe_duration") == 3

    def test_render_segment_called_once_per_segment(self, tmp_path: Path) -> None:
        """render_segment is invoked exactly once per audio segment."""
        call_log: list[str] = []
        audio_result = _make_audio_result(num_segments=3)
        pipeline, _ = _make_pipeline(tmp_path, call_log)

        pipeline.assemble_video(audio_result)

        assert call_log.count("render_segment") == 3

    def test_concatenate_and_validate_called_exactly_once(self, tmp_path: Path) -> None:
        """concatenate_segments and validate are each invoked exactly once."""
        call_log: list[str] = []
        audio_result = _make_audio_result(num_segments=3)
        pipeline, _ = _make_pipeline(tmp_path, call_log)

        pipeline.assemble_video(audio_result)

        assert call_log.count("concatenate_segments") == 1
        assert call_log.count("validate") == 1


class TestErrorPropagation:
    """Tests verifying each dependency's errors propagate unmodified."""

    def test_image_loader_failure_propagates(self, tmp_path: Path) -> None:
        """An ImageLoadError from image_loader propagates unmodified."""
        call_log: list[str] = []
        pipeline, _ = _make_pipeline(
            tmp_path, call_log, image_loader_error=ImageLoadError("no image found")
        )

        with pytest.raises(ImageLoadError, match="no image found"):
            pipeline.assemble_video(_make_audio_result(num_segments=1))

    def test_duration_probe_failure_propagates(self, tmp_path: Path) -> None:
        """An FFmpegError from probe_duration propagates unmodified."""
        call_log: list[str] = []
        pipeline, _ = _make_pipeline(
            tmp_path, call_log, probe_error=FFmpegError("ffprobe crashed")
        )

        with pytest.raises(FFmpegError, match="ffprobe crashed"):
            pipeline.assemble_video(_make_audio_result(num_segments=1))

    def test_subtitle_builder_failure_propagates(self, tmp_path: Path) -> None:
        """A SubtitleTimingError from subtitle_builder propagates unmodified."""
        call_log: list[str] = []
        pipeline, _ = _make_pipeline(
            tmp_path,
            call_log,
            subtitle_builder_error=SubtitleTimingError("bad timing"),
        )

        with pytest.raises(SubtitleTimingError, match="bad timing"):
            pipeline.assemble_video(_make_audio_result(num_segments=1))

    def test_render_failure_propagates(self, tmp_path: Path) -> None:
        """An FFmpegError from render_segment propagates unmodified."""
        call_log: list[str] = []
        pipeline, _ = _make_pipeline(
            tmp_path, call_log, render_error=FFmpegError("render failed")
        )

        with pytest.raises(FFmpegError, match="render failed"):
            pipeline.assemble_video(_make_audio_result(num_segments=1))

    def test_concatenate_failure_propagates(self, tmp_path: Path) -> None:
        """An FFmpegError from concatenate_segments propagates unmodified."""
        call_log: list[str] = []
        pipeline, _ = _make_pipeline(
            tmp_path, call_log, concatenate_error=FFmpegError("concat failed")
        )

        with pytest.raises(FFmpegError, match="concat failed"):
            pipeline.assemble_video(_make_audio_result(num_segments=1))

    def test_validator_failure_propagates(self, tmp_path: Path) -> None:
        """A VideoValidationError from the validator propagates unmodified."""
        call_log: list[str] = []
        pipeline, _ = _make_pipeline(
            tmp_path,
            call_log,
            validator_error=VideoValidationError("validation failed"),
        )

        with pytest.raises(VideoValidationError, match="validation failed"):
            pipeline.assemble_video(_make_audio_result(num_segments=1))


class TestDependencyInjection:
    """Tests verifying dependencies are genuinely swappable."""

    def test_swapping_image_loader_changes_resulting_image_paths(
        self, tmp_path: Path
    ) -> None:
        """A different injected image_loader changes the resulting image paths."""
        call_log: list[str] = []
        settings = _make_settings(tmp_path)
        audio_result = _make_audio_result(num_segments=1)

        def custom_image_loader(image_dir: Path, segments):
            call_log.append("image_loader")
            return tuple(
                ImageAsset(index=s.index, file_path=Path("/custom") / f"{s.index}.jpg")
                for s in segments
            )

        pipeline = VideoPipeline(
            image_loader=custom_image_loader,
            subtitle_builder=_FakeSubtitleBuilder(call_log),
            ffmpeg_service=_FakeFFmpegService(call_log),
            video_validator=_FakeVideoValidator(call_log),
            settings=settings,
        )

        result = pipeline.assemble_video(audio_result)

        assert result.segments[0].image_path == Path("/custom/0.jpg")

    def test_no_concrete_service_is_instantiated_internally(self, tmp_path: Path) -> None:
        """The pipeline module never imports a concrete service implementation."""
        import inspect

        from app.pipeline import video_pipeline

        source = inspect.getsource(video_pipeline)

        assert "ImageLoader()" not in source
        assert "FFmpegService()" not in source
        assert "VideoValidator()" not in source
        assert "from app.services" not in source


class TestEmptyInput:
    """Tests for an AudioGenerationResult with zero segments."""

    def test_empty_segments_produces_empty_result(self, tmp_path: Path) -> None:
        """Zero narration segments produce a VideoAssemblyResult with no segments."""
        call_log: list[str] = []
        pipeline, _ = _make_pipeline(tmp_path, call_log)
        audio_result = _make_audio_result(num_segments=0)

        result = pipeline.assemble_video(audio_result)

        assert result.segments == ()
        assert result.total_duration_seconds == 0.0

    def test_empty_segments_still_calls_concatenate_and_validate(
        self, tmp_path: Path
    ) -> None:
        """Even with zero segments, concatenate and validate are still invoked."""
        call_log: list[str] = []
        pipeline, _ = _make_pipeline(tmp_path, call_log)
        audio_result = _make_audio_result(num_segments=0)

        pipeline.assemble_video(audio_result)

        assert "concatenate_segments" in call_log
        assert "validate" in call_log
        assert "render_segment" not in call_log


class TestMultipleSegments:
    """Tests for a multi-segment (introduction + topics + conclusion) video."""

    def test_four_segments_all_processed_correctly(self, tmp_path: Path) -> None:
        """A 4-segment script produces 4 correctly-ordered VideoSegmentPlans."""
        call_log: list[str] = []
        audio_result = _make_audio_result(num_segments=4)
        pipeline, _ = _make_pipeline(tmp_path, call_log)

        result = pipeline.assemble_video(audio_result)

        assert len(result.segments) == 4
        assert [plan.index for plan in result.segments] == [0, 1, 2, 3]


class TestDeterminism:
    """Tests verifying repeated runs with equivalent fakes produce equal results."""

    def test_running_pipeline_twice_yields_equal_results(self, tmp_path: Path) -> None:
        """Two independent runs with equivalent fakes produce equal results."""
        audio_result = _make_audio_result(num_segments=2)
        durations = {
            str(segment.file_path): 4.0 for segment in audio_result.segments
        }

        call_log_1: list[str] = []
        pipeline_1, _ = _make_pipeline(tmp_path, call_log_1, durations=durations)
        result_1 = pipeline_1.assemble_video(audio_result)

        call_log_2: list[str] = []
        pipeline_2, _ = _make_pipeline(tmp_path, call_log_2, durations=durations)
        result_2 = pipeline_2.assemble_video(audio_result)

        assert result_1 == result_2
