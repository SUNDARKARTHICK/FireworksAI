"""Unit tests for the audio pipeline orchestrator (Component 6).

Scope is intentionally limited to
:func:`app.pipeline.audio_pipeline.run_audio_pipeline`. All
dependencies (Settings, TTSEngine, AudioWriter) are injected -
this test file never constructs concrete production implementations
like ``EdgeTTSEngine`` directly, and makes no real network calls.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from app.core.settings import Settings
from app.models.audio import AudioGenerationResult, AudioSegment, NarrationSegment
from app.models.script import Metadata, Script, Section
from app.pipeline import audio_pipeline
from app.pipeline.audio_pipeline import run_audio_pipeline
from app.services.audio_writer import FileAudioWriter
from app.services.tts_service import MockTTSEngine


class _FakeAudioWriter:
    """A fake AudioWriter test double that performs no real file I/O."""

    def __init__(self) -> None:
        self.calls: list[tuple[NarrationSegment, bytes, Path]] = []

    def write(
        self,
        segment: NarrationSegment,
        audio_bytes: bytes,
        output_dir: Path,
    ) -> AudioSegment:
        self.calls.append((segment, audio_bytes, output_dir))
        fake_path = output_dir / f"{segment.index:02d}_{segment.label}.mp3"
        return AudioSegment(segment=segment, file_path=fake_path)


def _make_script() -> Script:
    """Build a small Script fixture for pipeline tests."""
    return Script(
        metadata=Metadata(title="Test Lesson", author="Author", date="2026-07-30"),
        introduction="Welcome to FireworksAI in 2026.",
        sections=(
            Section(heading="First Topic", content="Content about first topic."),
            Section(heading="Second Topic", content="Content about second topic."),
        ),
        conclusion="That concludes this lesson.",
    )


def _make_settings(tmp_path: Path) -> Settings:
    return Settings(
        project_name="TestProject",
        version="0.0.1",
        default_language="en",
        default_voice="en-US-GuyNeural",
        log_level="INFO",
        base_dir=tmp_path,
    )


class TestRunAudioPipelineOrchestration:
    """Tests verifying the pipeline's orchestration sequence."""

    def test_returns_audio_generation_result(self, tmp_path: Path) -> None:
        """The pipeline returns an AudioGenerationResult referencing the script."""
        script = _make_script()
        settings = _make_settings(tmp_path)
        tts_engine = MockTTSEngine()
        audio_writer = _FakeAudioWriter()

        result = run_audio_pipeline(script, settings, tts_engine, audio_writer)

        assert isinstance(result, AudioGenerationResult)
        assert result.script is script

    def test_produces_one_audio_segment_per_narration_segment(
        self, tmp_path: Path
    ) -> None:
        """One AudioSegment is produced per narration segment (intro+2+conclusion)."""
        script = _make_script()
        settings = _make_settings(tmp_path)
        tts_engine = MockTTSEngine()
        audio_writer = _FakeAudioWriter()

        result = run_audio_pipeline(script, settings, tts_engine, audio_writer)

        assert len(result.segments) == 4

    def test_calls_tts_engine_once_per_segment_with_default_voice(
        self, tmp_path: Path
    ) -> None:
        """synthesize() is called once per segment, using settings.default_voice."""
        script = _make_script()
        settings = _make_settings(tmp_path)
        tts_engine = MockTTSEngine()
        audio_writer = _FakeAudioWriter()

        run_audio_pipeline(script, settings, tts_engine, audio_writer)

        assert len(tts_engine.calls) == 4
        assert all(voice == "en-US-GuyNeural" for _, voice in tts_engine.calls)

    def test_tts_engine_receives_normalized_text(self, tmp_path: Path) -> None:
        """The text passed to the TTS engine has already been normalized."""
        script = _make_script()
        settings = _make_settings(tmp_path)
        tts_engine = MockTTSEngine()
        audio_writer = _FakeAudioWriter()

        run_audio_pipeline(script, settings, tts_engine, audio_writer)

        introduction_text = tts_engine.calls[0][0]
        assert "Fireworks AI" in introduction_text
        assert "Twenty Twenty Six" in introduction_text
        assert "FireworksAI" not in introduction_text

    def test_calls_audio_writer_once_per_segment_with_audio_dir(
        self, tmp_path: Path
    ) -> None:
        """write() is called once per segment, targeting settings.audio_dir."""
        script = _make_script()
        settings = _make_settings(tmp_path)
        tts_engine = MockTTSEngine(fake_audio=b"FAKE_BYTES")
        audio_writer = _FakeAudioWriter()

        run_audio_pipeline(script, settings, tts_engine, audio_writer)

        assert len(audio_writer.calls) == 4
        assert all(output_dir == settings.audio_dir for _, _, output_dir in audio_writer.calls)
        assert all(audio_bytes == b"FAKE_BYTES" for _, audio_bytes, _ in audio_writer.calls)

    def test_segments_are_returned_in_narration_order(self, tmp_path: Path) -> None:
        """Returned AudioSegments preserve introduction -> sections -> conclusion order."""
        script = _make_script()
        settings = _make_settings(tmp_path)
        tts_engine = MockTTSEngine()
        audio_writer = _FakeAudioWriter()

        result = run_audio_pipeline(script, settings, tts_engine, audio_writer)

        labels = [segment.segment.label for segment in result.segments]
        assert labels == ["introduction", "first-topic", "second-topic", "conclusion"]

    def test_accepts_custom_acronym_lookup(self, tmp_path: Path) -> None:
        """A custom acronym lookup is passed through to the text normalizer."""
        script = _make_script()
        settings = _make_settings(tmp_path)
        tts_engine = MockTTSEngine()
        audio_writer = _FakeAudioWriter()

        run_audio_pipeline(
            script,
            settings,
            tts_engine,
            audio_writer,
            acronym_lookup={"FireworksAI": "Custom Expansion"},
        )

        introduction_text = tts_engine.calls[0][0]
        assert "Custom Expansion" in introduction_text


class TestRunAudioPipelineDependencyInjection:
    """Tests verifying the pipeline never constructs concrete implementations."""

    def test_pipeline_source_does_not_reference_file_namer(self) -> None:
        """The pipeline module never imports or references file_namer directly."""
        source = inspect.getsource(audio_pipeline)

        assert "file_namer" not in source
        assert "build_filename" not in source

    def test_pipeline_source_does_not_import_edge_tts(self) -> None:
        """The pipeline module never imports the concrete edge_tts library."""
        source = inspect.getsource(audio_pipeline)

        assert "edge_tts" not in source
        assert "EdgeTTSEngine" not in source

    def test_works_with_real_file_audio_writer(self, tmp_path: Path) -> None:
        """The pipeline works end-to-end with the real FileAudioWriter and disk I/O."""
        script = _make_script()
        settings = _make_settings(tmp_path)
        tts_engine = MockTTSEngine(fake_audio=b"REAL_FAKE_AUDIO")
        audio_writer = FileAudioWriter()

        result = run_audio_pipeline(script, settings, tts_engine, audio_writer)

        assert len(result.segments) == 4
        for audio_segment in result.segments:
            assert audio_segment.file_path.exists()
            assert audio_segment.file_path.read_bytes() == b"REAL_FAKE_AUDIO"
            assert audio_segment.file_path.parent == settings.audio_dir

    def test_swapping_audio_writer_implementation_requires_no_pipeline_change(
        self, tmp_path: Path
    ) -> None:
        """Swapping AudioWriter implementations doesn't change calling code."""
        script = _make_script()
        settings = _make_settings(tmp_path)
        tts_engine = MockTTSEngine()

        fake_result = run_audio_pipeline(
            script, settings, tts_engine, _FakeAudioWriter()
        )
        real_result = run_audio_pipeline(
            script, settings, MockTTSEngine(), FileAudioWriter()
        )

        assert len(fake_result.segments) == len(real_result.segments)


class TestRunAudioPipelineErrorPropagation:
    """Tests verifying errors from injected dependencies propagate correctly."""

    def test_tts_generation_error_propagates(self, tmp_path: Path) -> None:
        """A TTSGenerationError raised by the engine propagates unmodified."""
        from app.exceptions import TTSGenerationError

        class _FailingTTSEngine:
            def synthesize(self, text: str, voice: str) -> bytes:
                raise TTSGenerationError("synthesis failed")

        script = _make_script()
        settings = _make_settings(tmp_path)

        with pytest.raises(TTSGenerationError, match="synthesis failed"):
            run_audio_pipeline(script, settings, _FailingTTSEngine(), _FakeAudioWriter())

    def test_audio_write_error_propagates(self, tmp_path: Path) -> None:
        """An AudioWriteError raised by the writer propagates unmodified."""
        from app.exceptions import AudioWriteError

        class _FailingAudioWriter:
            def write(
                self,
                segment: NarrationSegment,
                audio_bytes: bytes,
                output_dir: Path,
            ) -> AudioSegment:
                raise AudioWriteError("write failed")

        script = _make_script()
        settings = _make_settings(tmp_path)
        tts_engine = MockTTSEngine()

        with pytest.raises(AudioWriteError, match="write failed"):
            run_audio_pipeline(script, settings, tts_engine, _FailingAudioWriter())
