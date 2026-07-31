"""Audio file writing service.

This module is responsible for safely persisting audio bytes to disk
under a given output directory and filename. It performs no narration
or TTS logic. It defines:

* :func:`write_audio_file`: the low-level primitive that safely writes
  raw bytes to a given path (no filename generation).
* :class:`AudioWriter`: an injectable Protocol used by
  :mod:`app.pipeline.audio_pipeline`, so the pipeline never needs to
  know how filenames are generated or how bytes are persisted.
* :class:`FileAudioWriter`: the concrete implementation of
  :class:`AudioWriter`, which internally generates each segment's
  filename via :mod:`app.utils.file_namer` and writes it via
  :func:`write_audio_file`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from app.exceptions import AudioWriteError
from app.models.audio import AudioSegment, NarrationSegment
from app.utils.file_namer import build_filename


def write_audio_file(
    audio_bytes: bytes,
    output_dir: Path,
    filename: str,
) -> Path:
    """Write audio bytes to a file under the given output directory.

    Creates ``output_dir`` (and any missing parent directories) if it
    does not already exist. If a file already exists at the target
    path, it is overwritten.

    Args:
        audio_bytes: The raw audio bytes to write. Must be non-empty.
        output_dir: The directory the audio file should be written
            into. Created automatically if it does not exist.
        filename: The filename to write to, e.g.
            ``"00_introduction.mp3"``. Must be a single path segment
            (no directory separators or parent-directory references).

    Returns:
        The :class:`pathlib.Path` of the written audio file.

    Raises:
        AudioWriteError: If ``audio_bytes`` is empty, if ``filename``
            is unsafe, if the output directory cannot be created, or
            if the write operation fails due to an OS-level error.
    """
    if not audio_bytes:
        raise AudioWriteError("Cannot write empty audio data to disk.")

    if not filename or Path(filename).name != filename:
        raise AudioWriteError(
            f"Invalid filename '{filename}': must be a single path "
            "segment with no directory separators or parent references."
        )

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AudioWriteError(
            f"Failed to create output directory '{output_dir}': {exc}"
        ) from exc

    file_path = output_dir / filename

    try:
        file_path.write_bytes(audio_bytes)
    except OSError as exc:
        raise AudioWriteError(
            f"Failed to write audio file '{file_path}': {exc}"
        ) from exc

    return file_path


@runtime_checkable
class AudioWriter(Protocol):
    """Abstraction for persisting a narration segment's audio to disk.

    Downstream orchestration (see :mod:`app.pipeline.audio_pipeline`)
    depends only on this interface, never on a concrete implementation
    or on filename-generation details.
    """

    def write(
        self,
        segment: NarrationSegment,
        audio_bytes: bytes,
        output_dir: Path,
    ) -> AudioSegment:
        """Persist a narration segment's audio and return the result.

        Args:
            segment: The narration segment the audio was synthesized
                from.
            audio_bytes: The raw audio bytes to persist.
            output_dir: The directory the audio file should be written
                into.

        Returns:
            An :class:`~app.models.audio.AudioSegment` describing the
            written file.

        Raises:
            AudioWriteError: If the audio cannot be persisted.
        """
        ...


class FileAudioWriter:
    """The default :class:`AudioWriter`: writes one MP3 file per segment.

    Generates each segment's filename internally via
    :func:`app.utils.file_namer.build_filename`, then writes the audio
    bytes via :func:`write_audio_file`. Callers never need to generate
    or know about filenames themselves.
    """

    def write(
        self,
        segment: NarrationSegment,
        audio_bytes: bytes,
        output_dir: Path,
    ) -> AudioSegment:
        """Generate a filename for the segment and persist its audio.

        Args:
            segment: The narration segment the audio was synthesized
                from.
            audio_bytes: The raw audio bytes to persist.
            output_dir: The directory the audio file should be written
                into.

        Returns:
            An :class:`~app.models.audio.AudioSegment` referencing the
            segment and the path of the written file.

        Raises:
            AudioWriteError: If the audio cannot be persisted.
        """
        filename = build_filename(segment)
        file_path = write_audio_file(audio_bytes, output_dir, filename)
        return AudioSegment(segment=segment, file_path=file_path)

