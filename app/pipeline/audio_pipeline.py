"""Audio generation pipeline orchestration.

This module coordinates the Milestone 3 audio generation sequence:
build narration segments from a Script, normalize their text, sort
each through a TTS engine, and persist each result through an audio
writer. It contains no narration-splitting logic, no text
normalization logic, no TTS logic, no filename generation, and no
direct file I/O — all of that is delegated to injected dependencies
and existing services.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.core.settings import Settings
from app.models.audio import AudioGenerationResult, AudioSegment
from app.models.script import Script
from app.services.audio_writer import AudioWriter
from app.services.narration_builder import build_narration_segments
from app.services.text_normalizer import normalize_segment
from app.services.tts_service import TTSEngine


def run_audio_pipeline(
    script: Script,
    settings: Settings,
    tts_engine: TTSEngine,
    audio_writer: AudioWriter,
    acronym_lookup: Mapping[str, str] | None = None,
) -> AudioGenerationResult:
    """Run the audio generation pipeline for a parsed Script.

    Sequence:
        1. Build ordered narration segments from ``script``.
        2. Normalize each segment's text for pronunciation.
        3. Synthesize audio for each normalized segment via
           ``tts_engine``.
        4. Persist each segment's audio via ``audio_writer``.
        5. Return an :class:`~app.models.audio.AudioGenerationResult`.

    Args:
        script: The parsed lesson script to narrate.
        settings: Application settings, used for the target audio
            output directory (``settings.audio_dir``) and the default
            TTS voice (``settings.default_voice``).
        tts_engine: An injected text-to-speech engine implementing
            :class:`~app.services.tts_service.TTSEngine`, used to
            synthesize audio for each segment. This function never
            constructs a concrete engine itself.
        audio_writer: An injected audio writer implementing
            :class:`~app.services.audio_writer.AudioWriter`, used to
            persist each segment's audio to disk. This function never
            generates filenames and never constructs a concrete writer
            itself.
        acronym_lookup: Optional custom acronym/brand expansion table
            passed through to the text normalizer. Defaults to the
            normalizer's built-in table when not provided.

    Returns:
        An :class:`~app.models.audio.AudioGenerationResult` containing
        the source script and one :class:`~app.models.audio.AudioSegment`
        per narration segment, in narration order.

    Raises:
        TTSGenerationError: If audio synthesis fails for any segment.
        AudioWriteError: If persisting a segment's audio fails.
    """
    raw_segments = build_narration_segments(script)
    normalized_segments = tuple(
        normalize_segment(segment, acronym_lookup=acronym_lookup)
        for segment in raw_segments
    )

    audio_segments: list[AudioSegment] = []
    for segment in normalized_segments:
        audio_bytes = tts_engine.synthesize(segment.text, settings.default_voice)
        audio_segment = audio_writer.write(segment, audio_bytes, settings.audio_dir)
        audio_segments.append(audio_segment)

    return AudioGenerationResult(script=script, segments=tuple(audio_segments))
