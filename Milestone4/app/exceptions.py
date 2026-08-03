"""Custom exception types shared across the FireworksAI application.

This module intentionally contains only exception class declarations.
It has no external dependencies and no business logic, so it can be
safely imported from any layer of the application without introducing
circular imports or coupling.
"""

from __future__ import annotations


class FireworksAIError(Exception):
    """Base class for all FireworksAI application-specific errors.

    All custom exceptions in this project should inherit from this
    class so that calling code can catch a single base type when it
    only cares that *some* FireworksAI error occurred.
    """


class ConfigurationError(FireworksAIError):
    """Raised when application configuration is missing or invalid.

    Examples:
        Raised when a required environment variable is absent, or when
        a configuration value fails validation (e.g. an empty project
        name or an invalid log level).
    """


class PipelineError(FireworksAIError):
    """Raised when the workflow/pipeline fails to execute correctly.

    Examples:
        Raised when a pipeline stage cannot complete initialization or
        cannot hand off to the next stage.
    """


class ValidationError(FireworksAIError):
    """Raised when a value fails a validation check.

    Examples:
        Raised when user-supplied or environment-supplied data does
        not satisfy the constraints required by the application.
    """


class FileLoadError(FireworksAIError):
    """Raised when a source file cannot be safely loaded from disk.

    Examples:
        Raised when a Markdown file does not exist, is not a regular
        file, or cannot be read due to an OS-level error (e.g.
        permissions, encoding).
    """


class MarkdownParsingError(FireworksAIError):
    """Raised when Markdown content cannot be parsed into a Script.

    Examples:
        Raised when YAML front matter is missing or invalid, when
        required metadata fields are absent, or when the expected
        introduction/section/conclusion structure is not present.
    """


class TTSGenerationError(FireworksAIError):
    """Raised when text-to-speech audio synthesis fails.

    Examples:
        Raised when the text or voice supplied to a
        :class:`~app.services.tts_service.TTSEngine` implementation is
        invalid, when the underlying TTS provider raises an error, or
        when no audio data is returned by the provider.
    """


class AudioWriteError(FireworksAIError):
    """Raised when audio bytes cannot be safely written to disk.

    Examples:
        Raised when the output directory cannot be created, when the
        supplied filename is unsafe (e.g. contains path separators or
        parent-directory references), when the audio bytes are empty,
        or when the underlying write operation fails due to an
        OS-level error.
    """


class SubtitleTimingError(FireworksAIError):
    """Raised when subtitle cue timing cannot be computed.

    Examples:
        Raised when an :class:`~app.models.audio.AudioSegment` passed
        to :func:`~app.services.subtitle_builder.build_subtitle_cues`
        has a missing (``None``) or non-positive ``duration_seconds``
        value.
    """


class ImageLoadError(FireworksAIError):
    """Raised when an image asset cannot be discovered or loaded.

    Examples:
        Raised when the configured image directory does not exist or
        is not a directory, or when no supported image file
        (``.png``, ``.jpg``, ``.jpeg``, ``.webp``) can be found for a
        given narration segment.
    """


class FFmpegError(FireworksAIError):
    """Raised when an FFmpeg/FFprobe operation fails.

    Examples:
        Raised when the ``ffmpeg`` or ``ffprobe`` executable cannot
        be found on the system PATH, when a required input file does
        not exist, when the underlying process exits with a non-zero
        return code, or when its output cannot be parsed as expected.
    """


class VideoValidationError(FireworksAIError):
    """Raised when a rendered video fails validation.

    Examples:
        Raised when the video file does not exist, has an unsupported
        extension, is empty, has a non-positive measured duration, or
        has a measured duration that differs from the expected
        duration by more than the configured tolerance.
    """


