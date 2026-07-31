"""Unit tests for the audio writer service (Component 5, extended in Component 6).

Scope covers :func:`app.services.audio_writer.write_audio_file` (the
low-level primitive) and the newly added
:class:`app.services.audio_writer.AudioWriter` Protocol /
:class:`app.services.audio_writer.FileAudioWriter` implementation
introduced for Component 6's dependency injection. All I/O happens
under pytest's ``tmp_path`` fixture.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.exceptions import AudioWriteError
from app.models.audio import AudioSegment, NarrationSegment
from app.services.audio_writer import AudioWriter, FileAudioWriter, write_audio_file


class TestWriteAudioFile:
    """Tests for :func:`write_audio_file`."""

    def test_writes_file_and_returns_path(self, tmp_path: Path) -> None:
        """Writing audio bytes returns a Path pointing to the written file."""
        result = write_audio_file(b"FAKE_MP3", tmp_path, "00_introduction.mp3")

        assert isinstance(result, Path)
        assert result == tmp_path / "00_introduction.mp3"
        assert result.exists()

    def test_file_contents_match_exactly(self, tmp_path: Path) -> None:
        """The written file's bytes match exactly what was passed in."""
        audio_bytes = b"\x00\x01\x02FAKE_AUDIO_DATA\xff"

        result = write_audio_file(audio_bytes, tmp_path, "01_history.mp3")

        assert result.read_bytes() == audio_bytes

    def test_creates_missing_output_directory(self, tmp_path: Path) -> None:
        """A missing output directory (including nested parents) is created."""
        nested_dir = tmp_path / "phase01" / "audio"
        assert not nested_dir.exists()

        result = write_audio_file(b"FAKE_MP3", nested_dir, "00_introduction.mp3")

        assert nested_dir.exists()
        assert nested_dir.is_dir()
        assert result.parent == nested_dir

    def test_does_not_error_if_output_directory_already_exists(
        self, tmp_path: Path
    ) -> None:
        """An already-existing output directory is reused without error."""
        tmp_path.mkdir(parents=True, exist_ok=True)

        result = write_audio_file(b"FAKE_MP3", tmp_path, "00_introduction.mp3")

        assert result.exists()

    def test_overwrites_existing_file_completely(self, tmp_path: Path) -> None:
        """Writing to an existing filename replaces the previous content."""
        first_path = write_audio_file(b"OLD_CONTENT", tmp_path, "00_intro.mp3")
        second_path = write_audio_file(b"NEW", tmp_path, "00_intro.mp3")

        assert first_path == second_path
        assert second_path.read_bytes() == b"NEW"

    def test_empty_audio_bytes_raises_audio_write_error(self, tmp_path: Path) -> None:
        """Passing empty audio bytes raises AudioWriteError."""
        with pytest.raises(AudioWriteError, match="empty audio"):
            write_audio_file(b"", tmp_path, "00_intro.mp3")

    def test_filename_with_directory_separator_raises_error(
        self, tmp_path: Path
    ) -> None:
        """A filename containing a path separator raises AudioWriteError."""
        with pytest.raises(AudioWriteError, match="single path segment"):
            write_audio_file(b"FAKE_MP3", tmp_path, "sub/dir.mp3")

    def test_filename_with_parent_reference_raises_error(self, tmp_path: Path) -> None:
        """A filename referencing a parent directory raises AudioWriteError."""
        with pytest.raises(AudioWriteError, match="single path segment"):
            write_audio_file(b"FAKE_MP3", tmp_path, "../escape.mp3")

    def test_empty_filename_raises_error(self, tmp_path: Path) -> None:
        """An empty filename string raises AudioWriteError."""
        with pytest.raises(AudioWriteError):
            write_audio_file(b"FAKE_MP3", tmp_path, "")

    def test_directory_creation_failure_raises_audio_write_error(
        self, tmp_path: Path
    ) -> None:
        """A blocked directory path (a file where a directory is expected) raises AudioWriteError."""
        blocking_file = tmp_path / "blocked"
        blocking_file.write_text("I am a file, not a directory.")
        impossible_dir = blocking_file / "subdir"

        with pytest.raises(AudioWriteError, match="Failed to create output directory"):
            write_audio_file(b"FAKE_MP3", impossible_dir, "00_intro.mp3")

    def test_uses_pathlib_path_for_output_directory(self, tmp_path: Path) -> None:
        """The function accepts and returns pathlib.Path objects natively."""
        assert isinstance(tmp_path, Path)

        result = write_audio_file(b"FAKE_MP3", tmp_path, "00_intro.mp3")

        assert isinstance(result, Path)


class TestAudioWriterProtocol:
    """Tests verifying the AudioWriter Protocol contract."""

    def test_file_audio_writer_satisfies_protocol(self) -> None:
        """FileAudioWriter structurally satisfies the AudioWriter protocol."""
        writer: AudioWriter = FileAudioWriter()

        assert isinstance(writer, AudioWriter)

    def test_plain_object_does_not_satisfy_protocol(self) -> None:
        """An unrelated object without write() fails the protocol check."""

        class NotAWriter:
            pass

        assert not isinstance(NotAWriter(), AudioWriter)


class TestFileAudioWriter:
    """Tests for :class:`FileAudioWriter`."""

    def test_write_returns_audio_segment(self, tmp_path: Path) -> None:
        """write() returns an AudioSegment referencing the source segment."""
        segment = NarrationSegment(index=0, label="introduction", text="Hello.")
        writer = FileAudioWriter()

        result = writer.write(segment, b"FAKE_MP3", tmp_path)

        assert isinstance(result, AudioSegment)
        assert result.segment is segment

    def test_write_generates_filename_internally(self, tmp_path: Path) -> None:
        """write() derives the filename from the segment without external input."""
        segment = NarrationSegment(
            index=1, label="history-of-fireworks", text="Some history."
        )
        writer = FileAudioWriter()

        result = writer.write(segment, b"FAKE_MP3", tmp_path)

        assert result.file_path == tmp_path / "01_history-of-fireworks.mp3"

    def test_write_persists_correct_bytes(self, tmp_path: Path) -> None:
        """write() persists the exact audio bytes provided."""
        segment = NarrationSegment(index=0, label="introduction", text="Hello.")
        writer = FileAudioWriter()

        result = writer.write(segment, b"REAL_AUDIO_BYTES", tmp_path)

        assert result.file_path.read_bytes() == b"REAL_AUDIO_BYTES"

    def test_write_creates_output_directory(self, tmp_path: Path) -> None:
        """write() creates the output directory if it does not exist."""
        segment = NarrationSegment(index=0, label="introduction", text="Hello.")
        writer = FileAudioWriter()
        nested_dir = tmp_path / "phase01"

        writer.write(segment, b"FAKE_MP3", nested_dir)

        assert nested_dir.exists()

    def test_write_raises_audio_write_error_for_empty_bytes(
        self, tmp_path: Path
    ) -> None:
        """write() propagates AudioWriteError for empty audio bytes."""
        segment = NarrationSegment(index=0, label="introduction", text="Hello.")
        writer = FileAudioWriter()

        with pytest.raises(AudioWriteError):
            writer.write(segment, b"", tmp_path)

