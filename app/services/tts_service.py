"""Text-to-speech synthesis service.

This module defines the text-to-speech abstraction (:class:`TTSEngine`)
used throughout the audio pipeline, along with two implementations:
:class:`EdgeTTSEngine` (a real implementation backed by the
``edge-tts`` library) and :class:`MockTTSEngine` (a deterministic test
double). Downstream components depend only on the :class:`TTSEngine`
abstraction, never on a concrete implementation, following the
Dependency Inversion Principle.

This module performs no file writing, no filename/slug generation, no
text normalization, and no pipeline orchestration. ``asyncio`` usage
is fully contained inside :class:`EdgeTTSEngine`; every public method
in this module is synchronous.
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol, runtime_checkable

import edge_tts

from app.exceptions import TTSGenerationError


@runtime_checkable
class TTSEngine(Protocol):
    """Abstraction for a text-to-speech synthesis engine.

    Any class implementing this protocol can be used by the audio
    pipeline, regardless of which underlying TTS provider it wraps.
    """

    def synthesize(self, text: str, voice: str) -> bytes:
        """Synthesize speech audio for the given text and voice.

        Args:
            text: The text to synthesize into speech.
            voice: The identifier of the voice to use for synthesis.

        Returns:
            Raw audio bytes (e.g. MP3-encoded data).

        Raises:
            TTSGenerationError: If synthesis fails for any reason.
        """
        ...


class EdgeTTSEngine:
    """A :class:`TTSEngine` implementation backed by the edge-tts library.

    This engine receives text and a voice identifier and returns raw
    MP3 audio bytes. It has no knowledge of where audio files are
    stored, how narration segments are labeled, or how the pipeline is
    orchestrated — it only performs synthesis.

    All ``asyncio`` usage is contained within this class; the public
    :meth:`synthesize` method is fully synchronous.
    """

    def __init__(
        self,
        communicate_factory: Any = None,
    ) -> None:
        """Initialize the engine.

        Args:
            communicate_factory: A callable of the form
                ``factory(text, voice) -> object`` returning an object
                exposing an async ``stream()`` generator, matching the
                interface of :class:`edge_tts.Communicate`. Defaults to
                ``edge_tts.Communicate`` itself. Injectable so tests
                can substitute a fake communicator with no network
                access.
        """
        self._communicate_factory = (
            communicate_factory
            if communicate_factory is not None
            else edge_tts.Communicate
        )

    def synthesize(self, text: str, voice: str) -> bytes:
        """Synthesize speech audio for the given text and voice.

        Args:
            text: The text to synthesize into speech. Must be
                non-empty after stripping whitespace.
            voice: The identifier of the voice to use (e.g.
                ``"en-US-GuyNeural"``). Must be non-empty after
                stripping whitespace.

        Returns:
            Raw MP3-encoded audio bytes.

        Raises:
            TTSGenerationError: If ``text`` or ``voice`` is empty, if
                the underlying TTS provider raises an error, or if no
                audio data is returned.
        """
        if not text or not text.strip():
            raise TTSGenerationError("Cannot synthesize audio for empty text.")
        if not voice or not voice.strip():
            raise TTSGenerationError("A non-empty voice identifier is required.")

        try:
            return asyncio.run(self._synthesize_async(text, voice))
        except TTSGenerationError:
            raise
        except Exception as exc:
            raise TTSGenerationError(
                f"Failed to synthesize audio for voice '{voice}': {exc}"
            ) from exc

    async def _synthesize_async(self, text: str, voice: str) -> bytes:
        """Perform the actual asynchronous synthesis and byte collection.

        Args:
            text: The text to synthesize.
            voice: The voice identifier to use.

        Returns:
            The concatenated raw audio bytes from all audio chunks.

        Raises:
            TTSGenerationError: If no audio chunks are returned by the
                communicator.
        """
        communicator = self._communicate_factory(text, voice)
        audio_chunks = bytearray()

        async for chunk in communicator.stream():
            if chunk.get("type") == "audio":
                audio_chunks.extend(chunk["data"])

        if not audio_chunks:
            raise TTSGenerationError(
                "No audio data was returned by the TTS provider."
            )

        return bytes(audio_chunks)


class MockTTSEngine:
    """A deterministic :class:`TTSEngine` test double with no network calls.

    Returns a fixed, configurable byte string for every call and
    records each call's arguments for later assertions in tests.
    """

    def __init__(self, fake_audio: bytes = b"FAKE_MP3") -> None:
        """Initialize the mock engine.

        Args:
            fake_audio: The fixed byte string returned by every call
                to :meth:`synthesize`.
        """
        self._fake_audio = fake_audio
        self.calls: list[tuple[str, str]] = []

    def synthesize(self, text: str, voice: str) -> bytes:
        """Record the call and return the configured fake audio bytes.

        Args:
            text: The text that would have been synthesized.
            voice: The voice identifier that would have been used.

        Returns:
            The fixed fake audio bytes configured at construction time.
        """
        self.calls.append((text, voice))
        return self._fake_audio
