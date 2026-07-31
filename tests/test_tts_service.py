"""Unit tests for the TTS service (Component 4).

Scope is intentionally limited to
:class:`app.services.tts_service.TTSEngine`,
:class:`app.services.tts_service.EdgeTTSEngine`, and
:class:`app.services.tts_service.MockTTSEngine`.

No real network calls are made in any test. `EdgeTTSEngine` is always
exercised with an injected fake communicate factory.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.exceptions import TTSGenerationError
from app.services.tts_service import EdgeTTSEngine, MockTTSEngine, TTSEngine


class _FakeCommunicate:
    """A fake stand-in for edge_tts.Communicate with no network access."""

    def __init__(
        self,
        text: str,
        voice: str,
        chunks: list[dict[str, Any]] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.text = text
        self.voice = voice
        self._chunks = chunks if chunks is not None else []
        self._error = error

    async def stream(self):
        """Yield configured fake chunks, or raise a configured error."""
        if self._error is not None:
            raise self._error
        for chunk in self._chunks:
            yield chunk


def _make_success_factory(audio_parts: list[bytes]):
    """Build a communicate_factory that yields the given audio parts."""

    def factory(text: str, voice: str) -> _FakeCommunicate:
        chunks = [{"type": "audio", "data": part} for part in audio_parts]
        chunks.append({"type": "WordBoundary", "offset": 0, "duration": 0})
        return _FakeCommunicate(text, voice, chunks=chunks)

    return factory


def _make_error_factory(error: Exception):
    """Build a communicate_factory whose stream() raises the given error."""

    def factory(text: str, voice: str) -> _FakeCommunicate:
        return _FakeCommunicate(text, voice, error=error)

    return factory


def _make_empty_factory():
    """Build a communicate_factory that yields no audio chunks at all."""

    def factory(text: str, voice: str) -> _FakeCommunicate:
        return _FakeCommunicate(text, voice, chunks=[])

    return factory


class TestTTSEngineProtocol:
    """Tests verifying the TTSEngine Protocol contract."""

    def test_mock_engine_satisfies_protocol(self) -> None:
        """MockTTSEngine structurally satisfies the TTSEngine protocol."""
        engine: TTSEngine = MockTTSEngine()

        assert isinstance(engine, TTSEngine)

    def test_edge_engine_satisfies_protocol(self) -> None:
        """EdgeTTSEngine structurally satisfies the TTSEngine protocol."""
        engine: TTSEngine = EdgeTTSEngine(communicate_factory=_make_empty_factory())

        assert isinstance(engine, TTSEngine)

    def test_plain_object_does_not_satisfy_protocol(self) -> None:
        """An unrelated object without synthesize() fails the protocol check."""

        class NotAnEngine:
            pass

        assert not isinstance(NotAnEngine(), TTSEngine)


class TestMockTTSEngine:
    """Tests for the MockTTSEngine test double."""

    def test_returns_default_fake_audio(self) -> None:
        """MockTTSEngine returns the default fake audio bytes."""
        engine = MockTTSEngine()

        result = engine.synthesize("Hello.", "en-US-GuyNeural")

        assert result == b"FAKE_MP3"

    def test_returns_configured_fake_audio(self) -> None:
        """MockTTSEngine returns a custom configured fake byte string."""
        engine = MockTTSEngine(fake_audio=b"CUSTOM_BYTES")

        result = engine.synthesize("Hello.", "en-US-GuyNeural")

        assert result == b"CUSTOM_BYTES"

    def test_makes_no_network_calls_and_records_calls(self) -> None:
        """MockTTSEngine records call arguments without any network access."""
        engine = MockTTSEngine()

        engine.synthesize("First segment.", "en-US-GuyNeural")
        engine.synthesize("Second segment.", "en-GB-RyanNeural")

        assert engine.calls == [
            ("First segment.", "en-US-GuyNeural"),
            ("Second segment.", "en-GB-RyanNeural"),
        ]


class TestEdgeTTSEngineInitialization:
    """Tests for EdgeTTSEngine construction and dependency injection."""

    def test_accepts_injected_communicate_factory(self) -> None:
        """A custom communicate_factory can be injected at construction."""
        factory = _make_success_factory([b"abc"])

        engine = EdgeTTSEngine(communicate_factory=factory)

        assert engine._communicate_factory is factory

    def test_defaults_to_edge_tts_communicate_when_not_injected(self) -> None:
        """With no factory injected, the engine defaults to edge_tts.Communicate."""
        import edge_tts

        engine = EdgeTTSEngine()

        assert engine._communicate_factory is edge_tts.Communicate


class TestEdgeTTSEngineSynthesis:
    """Tests for EdgeTTSEngine.synthesize, with all network calls mocked."""

    def test_synthesizes_and_concatenates_audio_chunks(self) -> None:
        """Multiple audio chunks are concatenated into a single byte string."""
        engine = EdgeTTSEngine(
            communicate_factory=_make_success_factory([b"chunk1", b"chunk2"])
        )

        result = engine.synthesize("Hello world.", "en-US-GuyNeural")

        assert result == b"chunk1chunk2"

    def test_ignores_non_audio_chunks(self) -> None:
        """Non-audio chunk types (e.g. WordBoundary) are ignored."""
        engine = EdgeTTSEngine(communicate_factory=_make_success_factory([b"only-audio"]))

        result = engine.synthesize("Hello world.", "en-US-GuyNeural")

        assert result == b"only-audio"


class TestEdgeTTSEngineInvalidInput:
    """Tests for invalid text/voice input handling."""

    def test_empty_text_raises_tts_generation_error(self) -> None:
        """An empty text string raises TTSGenerationError before synthesis."""
        engine = EdgeTTSEngine(communicate_factory=_make_success_factory([b"x"]))

        with pytest.raises(TTSGenerationError, match="empty text"):
            engine.synthesize("   ", "en-US-GuyNeural")

    def test_empty_voice_raises_tts_generation_error(self) -> None:
        """An empty voice string raises TTSGenerationError before synthesis."""
        engine = EdgeTTSEngine(communicate_factory=_make_success_factory([b"x"]))

        with pytest.raises(TTSGenerationError, match="voice"):
            engine.synthesize("Hello world.", "   ")

    def test_invalid_voice_from_provider_raises_tts_generation_error(self) -> None:
        """A provider-side error for an invalid voice is wrapped in TTSGenerationError."""
        engine = EdgeTTSEngine(
            communicate_factory=_make_error_factory(ValueError("Invalid voice name"))
        )

        with pytest.raises(TTSGenerationError, match="Invalid voice name"):
            engine.synthesize("Hello world.", "not-a-real-voice")


class TestEdgeTTSEngineExceptionHandling:
    """Tests for exception handling and wrapping behavior."""

    def test_provider_exception_is_wrapped_in_tts_generation_error(self) -> None:
        """Any unexpected exception from the provider is wrapped, not leaked."""
        engine = EdgeTTSEngine(
            communicate_factory=_make_error_factory(ConnectionError("network down"))
        )

        with pytest.raises(TTSGenerationError, match="network down"):
            engine.synthesize("Hello world.", "en-US-GuyNeural")

    def test_empty_audio_stream_raises_tts_generation_error(self) -> None:
        """A provider returning no audio chunks raises TTSGenerationError."""
        engine = EdgeTTSEngine(communicate_factory=_make_empty_factory())

        with pytest.raises(TTSGenerationError, match="No audio data"):
            engine.synthesize("Hello world.", "en-US-GuyNeural")

    def test_no_asyncio_object_leaks_to_caller(self) -> None:
        """The public synthesize() call returns plain bytes, not a coroutine."""
        engine = EdgeTTSEngine(communicate_factory=_make_success_factory([b"abc"]))

        result = engine.synthesize("Hello world.", "en-US-GuyNeural")

        assert isinstance(result, bytes)


class TestDependencyInjectionCompatibility:
    """Tests verifying both engines are interchangeable via the TTSEngine type."""

    @staticmethod
    def _narrate(engine: TTSEngine, text: str, voice: str) -> bytes:
        """A tiny helper simulating how a pipeline would depend on TTSEngine."""
        return engine.synthesize(text, voice)

    def test_mock_engine_works_through_protocol_typed_function(self) -> None:
        """A function typed against TTSEngine works with MockTTSEngine."""
        engine = MockTTSEngine(fake_audio=b"MOCK_BYTES")

        result = self._narrate(engine, "Hello.", "en-US-GuyNeural")

        assert result == b"MOCK_BYTES"

    def test_edge_engine_works_through_protocol_typed_function(self) -> None:
        """A function typed against TTSEngine works with EdgeTTSEngine."""
        engine = EdgeTTSEngine(communicate_factory=_make_success_factory([b"edge-bytes"]))

        result = self._narrate(engine, "Hello.", "en-US-GuyNeural")

        assert result == b"edge-bytes"

    def test_engines_are_swappable_without_changing_calling_code(self) -> None:
        """Swapping engine implementations requires no change to calling code."""
        engines: list[TTSEngine] = [
            MockTTSEngine(fake_audio=b"A"),
            EdgeTTSEngine(communicate_factory=_make_success_factory([b"B"])),
        ]

        results = [self._narrate(engine, "text", "voice") for engine in engines]

        assert results == [b"A", b"B"]
