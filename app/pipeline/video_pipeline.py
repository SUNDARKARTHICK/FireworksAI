"""Video assembly pipeline orchestration.

This module is the composition root of Milestone 4: it coordinates
image discovery, audio duration probing, subtitle cue building,
per-segment video rendering, concatenation, and validation into one
final MP4. It contains no business logic of its own - no timing
calculations, no filename generation policy, no subtitle text
calculations, no FFmpeg command construction, and no filesystem
searching. Every dependency is received via constructor injection as
a structurally-typed abstraction; this module never imports a service
module directly (only models, ``Settings``, and the shared
media-agnostic naming utility).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.core.config import Settings
from app.models.audio import AudioGenerationResult, AudioSegment, NarrationSegment
from app.models.video import (
    ImageAsset,
    SubtitleCue,
    VideoAssemblyResult,
    VideoSegmentPlan,
    VideoValidationResult,
)
from app.utils.segment_namer import build_segment_basename

#: Injected image discovery callable, matching
#: ``app.services.image_loader.load_images_for_segments``'s signature.
ImageLoaderFn = Callable[[Path, "tuple[NarrationSegment, ...]"], "tuple[ImageAsset, ...]"]

#: Injected subtitle cue builder callable, matching
#: ``app.services.subtitle_builder.build_subtitle_cues``'s signature.
SubtitleBuilderFn = Callable[["tuple[AudioSegment, ...]"], "tuple[SubtitleCue, ...]"]

_DEFAULT_OUTPUT_FILENAME = "final.mp4"
_CLIPS_SUBDIRECTORY = "clips"


@runtime_checkable
class VideoRenderer(Protocol):
    """Abstraction for everything this pipeline needs from FFmpeg.

    Structurally satisfied by
    :class:`~app.services.ffmpeg_service.FFmpegService`, without this
    module ever importing that class.
    """

    def probe_duration(self, path: Path) -> float:
        """Measure an audio file's duration, in seconds."""
        ...

    def render_segment(
        self,
        audio_path: Path,
        image_path: Path,
        subtitle: SubtitleCue,
        output_path: Path,
    ) -> Path:
        """Render one segment's clip and return its path."""
        ...

    def concatenate_segments(
        self,
        segment_paths: tuple[Path, ...],
        output_path: Path,
    ) -> Path:
        """Concatenate rendered clips into one final video path."""
        ...


@runtime_checkable
class Validator(Protocol):
    """Abstraction for validating a rendered video.

    Structurally satisfied by
    :class:`~app.services.video_validator.VideoValidator`, without
    this module ever importing that class.
    """

    def validate(
        self,
        video_path: Path,
        expected_duration_seconds: float,
    ) -> VideoValidationResult:
        """Validate a rendered video and return its validation result."""
        ...


class VideoPipeline:
    """Orchestrates image loading, rendering, concatenation, and validation.

    Every dependency is injected at construction time. This class
    never instantiates a concrete service implementation and never
    imports a service module.
    """

    def __init__(
        self,
        image_loader: ImageLoaderFn,
        subtitle_builder: SubtitleBuilderFn,
        ffmpeg_service: VideoRenderer,
        video_validator: Validator,
        settings: Settings,
        image_dir: Path | None = None,
        clips_dir: Path | None = None,
    ) -> None:
        """Initialize the pipeline.

        Args:
            image_loader: An injected callable matching
                ``load_images_for_segments(image_dir, segments) ->
                tuple[ImageAsset, ...]``.
            subtitle_builder: An injected callable matching
                ``build_subtitle_cues(audio_segments) ->
                tuple[SubtitleCue, ...]``.
            ffmpeg_service: An injected object satisfying
                :class:`VideoRenderer` (probing duration, rendering
                segments, and concatenating clips).
            video_validator: An injected object satisfying
                :class:`Validator`.
            settings: Application settings, used for
                ``settings.output_dir`` (final video location) and as
                the default source for ``image_dir``/``clips_dir``
                when not explicitly provided.
            image_dir: Directory to load segment images from. Defaults
                to ``settings.assets_dir``, since ``Settings`` (from
                Milestone 1) has no dedicated images directory field
                and this pipeline does not modify that file.
            clips_dir: Directory intermediate per-segment clips are
                rendered into before concatenation. Defaults to
                ``settings.output_dir / "clips"``.
        """
        self._image_loader = image_loader
        self._subtitle_builder = subtitle_builder
        self._ffmpeg_service = ffmpeg_service
        self._video_validator = video_validator
        self._settings = settings
        self._image_dir = image_dir if image_dir is not None else settings.assets_dir
        self._clips_dir = (
            clips_dir if clips_dir is not None else settings.output_dir / _CLIPS_SUBDIRECTORY
        )

    def assemble_video(
        self,
        audio_result: AudioGenerationResult,
        output_filename: str = _DEFAULT_OUTPUT_FILENAME,
    ) -> VideoAssemblyResult:
        """Assemble a final MP4 video from a narrated AudioGenerationResult.

        Sequence: load one image per segment, probe every audio
        segment's real duration, build subtitle cues from those
        durations, render each segment's clip, concatenate every clip,
        validate the result, and return a populated
        :class:`~app.models.video.VideoAssemblyResult`.

        Args:
            audio_result: The Milestone 3 output to assemble into
                video - the source Script plus one narrated
                :class:`~app.models.audio.AudioSegment` per narration
                segment.
            output_filename: The filename for the final concatenated
                video, written under ``settings.output_dir``. Defaults
                to ``"final.mp4"``.

        Returns:
            A :class:`~app.models.video.VideoAssemblyResult` describing
            the assembled video.

        Raises:
            ImageLoadError: If an image cannot be found for any segment.
            FFmpegError: If duration probing, segment rendering, or
                concatenation fails.
            SubtitleTimingError: If subtitle cue timing cannot be
                computed.
            VideoValidationError: If the finished video fails validation.
        """
        narration_segments = tuple(
            audio_segment.segment for audio_segment in audio_result.segments
        )

        image_assets = self._image_loader(self._image_dir, narration_segments)

        audio_segments_with_duration = tuple(
            AudioSegment(
                segment=audio_segment.segment,
                file_path=audio_segment.file_path,
                duration_seconds=self._ffmpeg_service.probe_duration(
                    audio_segment.file_path
                ),
            )
            for audio_segment in audio_result.segments
        )

        subtitle_cues = self._subtitle_builder(audio_segments_with_duration)

        video_segment_plans: list[VideoSegmentPlan] = []
        rendered_clip_paths: list[Path] = []

        for audio_segment, image_asset, cue in zip(
            audio_segments_with_duration, image_assets, subtitle_cues
        ):
            plan = VideoSegmentPlan(
                index=audio_segment.segment.index,
                label=audio_segment.segment.label,
                audio_path=audio_segment.file_path,
                image_path=image_asset.file_path,
                subtitle=cue,
            )
            video_segment_plans.append(plan)

            clip_basename = build_segment_basename(
                audio_segment.segment.index, audio_segment.segment.label
            )
            clip_output_path = self._clips_dir / f"{clip_basename}.mp4"

            rendered_path = self._ffmpeg_service.render_segment(
                audio_path=plan.audio_path,
                image_path=plan.image_path,
                subtitle=plan.subtitle,
                output_path=clip_output_path,
            )
            rendered_clip_paths.append(rendered_path)

        total_duration_seconds = float(
            sum(
                audio_segment.duration_seconds
                for audio_segment in audio_segments_with_duration
            )
        )

        final_output_path = self._settings.output_dir / output_filename
        concatenated_path = self._ffmpeg_service.concatenate_segments(
            segment_paths=tuple(rendered_clip_paths),
            output_path=final_output_path,
        )

        self._video_validator.validate(
            video_path=concatenated_path,
            expected_duration_seconds=total_duration_seconds,
        )

        return VideoAssemblyResult(
            script=audio_result.script,
            segments=tuple(video_segment_plans),
            output_path=concatenated_path,
            total_duration_seconds=total_duration_seconds,
        )
