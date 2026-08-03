"""Unit tests for the image discovery/loading service (Component 3).

Scope is intentionally limited to
:func:`app.services.image_loader.load_images_for_segments`. All
filesystem access happens under pytest's ``tmp_path`` fixture - no
real content directory is touched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.exceptions import ImageLoadError
from app.models.audio import NarrationSegment
from app.models.video import ImageAsset
from app.services.image_loader import load_images_for_segments


def _segments(*labels_with_index: tuple[int, str]) -> tuple[NarrationSegment, ...]:
    """Build NarrationSegment fixtures for the given (index, label) pairs."""
    return tuple(
        NarrationSegment(index=index, label=label, text=f"Text for {label}.")
        for index, label in labels_with_index
    )


class TestMissingOrInvalidDirectory:
    """Tests for invalid image_dir handling."""

    def test_missing_directory_raises_image_load_error(self, tmp_path: Path) -> None:
        """A non-existent image directory raises ImageLoadError."""
        missing_dir = tmp_path / "does_not_exist"
        segments = _segments((0, "introduction"))

        with pytest.raises(ImageLoadError, match="not found"):
            load_images_for_segments(missing_dir, segments)

    def test_file_instead_of_directory_raises_image_load_error(
        self, tmp_path: Path
    ) -> None:
        """A path pointing to a file instead of a directory raises ImageLoadError."""
        file_path = tmp_path / "not_a_directory.txt"
        file_path.write_text("I am a file.")
        segments = _segments((0, "introduction"))

        with pytest.raises(ImageLoadError, match="not a directory"):
            load_images_for_segments(file_path, segments)


class TestEmptyDirectory:
    """Tests for an existing but empty image directory."""

    def test_empty_directory_raises_image_load_error(self, tmp_path: Path) -> None:
        """An empty image directory raises ImageLoadError naming the segment."""
        segments = _segments((0, "introduction"))

        with pytest.raises(ImageLoadError, match="introduction"):
            load_images_for_segments(tmp_path, segments)

    def test_empty_segments_with_empty_directory_returns_empty_tuple(
        self, tmp_path: Path
    ) -> None:
        """No segments requested means no images required and no error."""
        result = load_images_for_segments(tmp_path, ())

        assert result == ()


class TestValidImageDiscovery:
    """Tests for successful image discovery."""

    def test_finds_single_png_image(self, tmp_path: Path) -> None:
        """A single matching PNG file is found and returned as an ImageAsset."""
        (tmp_path / "00_introduction.png").write_bytes(b"fake-png-bytes")
        segments = _segments((0, "introduction"))

        result = load_images_for_segments(tmp_path, segments)

        assert result == (
            ImageAsset(index=0, file_path=tmp_path / "00_introduction.png"),
        )

    def test_finds_jpg_and_jpeg_and_webp_images(self, tmp_path: Path) -> None:
        """JPG, JPEG, and WEBP extensions are each individually discoverable."""
        (tmp_path / "00_a.jpg").write_bytes(b"x")
        (tmp_path / "01_b.jpeg").write_bytes(b"x")
        (tmp_path / "02_c.webp").write_bytes(b"x")
        segments = _segments((0, "a"), (1, "b"), (2, "c"))

        result = load_images_for_segments(tmp_path, segments)

        assert result[0].file_path == tmp_path / "00_a.jpg"
        assert result[1].file_path == tmp_path / "01_b.jpeg"
        assert result[2].file_path == tmp_path / "02_c.webp"

    def test_returned_image_asset_is_immutable(self, tmp_path: Path) -> None:
        """The returned ImageAsset is a frozen dataclass."""
        (tmp_path / "00_introduction.png").write_bytes(b"x")
        segments = _segments((0, "introduction"))

        result = load_images_for_segments(tmp_path, segments)

        with pytest.raises(AttributeError):
            result[0].index = 99  # type: ignore[misc]


class TestCorrectOrdering:
    """Tests verifying result ordering matches input segment ordering."""

    def test_results_preserve_segment_order(self, tmp_path: Path) -> None:
        """ImageAssets are returned in the same order as the input segments."""
        (tmp_path / "00_introduction.png").write_bytes(b"x")
        (tmp_path / "01_history.png").write_bytes(b"x")
        (tmp_path / "02_conclusion.png").write_bytes(b"x")
        segments = _segments((0, "introduction"), (1, "history"), (2, "conclusion"))

        result = load_images_for_segments(tmp_path, segments)

        assert [asset.index for asset in result] == [0, 1, 2]
        assert result[0].file_path.name == "00_introduction.png"
        assert result[1].file_path.name == "01_history.png"
        assert result[2].file_path.name == "02_conclusion.png"


class TestUnsupportedExtension:
    """Tests for files with unsupported extensions."""

    def test_unsupported_extension_is_ignored_and_raises_error(
        self, tmp_path: Path
    ) -> None:
        """A .gif file (unsupported) is ignored; no match means an error."""
        (tmp_path / "00_introduction.gif").write_bytes(b"x")
        segments = _segments((0, "introduction"))

        with pytest.raises(ImageLoadError, match="No image found"):
            load_images_for_segments(tmp_path, segments)

    def test_unsupported_extension_ignored_when_supported_one_also_present(
        self, tmp_path: Path
    ) -> None:
        """An unsupported file alongside a supported one does not interfere."""
        (tmp_path / "00_introduction.gif").write_bytes(b"x")
        (tmp_path / "00_introduction.png").write_bytes(b"x")
        segments = _segments((0, "introduction"))

        result = load_images_for_segments(tmp_path, segments)

        assert result[0].file_path.name == "00_introduction.png"


class TestDuplicateHandling:
    """Tests for deterministic handling of duplicate matching filenames."""

    def test_png_is_preferred_over_jpg_when_both_present(self, tmp_path: Path) -> None:
        """When both .png and .jpg exist for a segment, .png is always chosen."""
        (tmp_path / "00_introduction.jpg").write_bytes(b"x")
        (tmp_path / "00_introduction.png").write_bytes(b"x")
        segments = _segments((0, "introduction"))

        result = load_images_for_segments(tmp_path, segments)

        assert result[0].file_path.name == "00_introduction.png"

    def test_duplicate_choice_is_deterministic_across_multiple_calls(
        self, tmp_path: Path
    ) -> None:
        """Repeated calls with the same duplicate files always pick the same one."""
        (tmp_path / "00_introduction.webp").write_bytes(b"x")
        (tmp_path / "00_introduction.jpeg").write_bytes(b"x")
        (tmp_path / "00_introduction.jpg").write_bytes(b"x")
        (tmp_path / "00_introduction.png").write_bytes(b"x")
        segments = _segments((0, "introduction"))

        first = load_images_for_segments(tmp_path, segments)
        second = load_images_for_segments(tmp_path, segments)

        assert first == second
        assert first[0].file_path.name == "00_introduction.png"


class TestMissingImageForOneSegment:
    """Tests verifying a partial match still raises clearly."""

    def test_missing_image_for_second_segment_raises_error_naming_it(
        self, tmp_path: Path
    ) -> None:
        """If only some segments have images, the error names the missing one."""
        (tmp_path / "00_introduction.png").write_bytes(b"x")
        segments = _segments((0, "introduction"), (1, "history"))

        with pytest.raises(ImageLoadError, match="history"):
            load_images_for_segments(tmp_path, segments)


class TestDeterminism:
    """Tests verifying overall deterministic behavior."""

    def test_is_deterministic_for_the_same_input(self, tmp_path: Path) -> None:
        """Calling load_images_for_segments twice yields identical results."""
        (tmp_path / "00_introduction.png").write_bytes(b"x")
        (tmp_path / "01_history.jpg").write_bytes(b"x")
        segments = _segments((0, "introduction"), (1, "history"))

        first = load_images_for_segments(tmp_path, segments)
        second = load_images_for_segments(tmp_path, segments)

        assert first == second
