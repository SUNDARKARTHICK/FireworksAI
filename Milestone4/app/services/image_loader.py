"""Image discovery service for video assembly.

This module matches one image file to each narration segment, given a
directory of images. It performs no image processing or resizing, no
subtitle logic, no FFmpeg invocation, and no pipeline orchestration -
it only discovers and validates image file paths, returning immutable
:class:`~app.models.video.ImageAsset` instances.

Expected image naming convention uses the shared, media-agnostic
``"<index>_<label>"`` basename from :mod:`app.utils.segment_namer` -
the same basename policy used for audio files, but resolved
independently here so the image subsystem has no dependency on
audio-specific naming code.
"""

from __future__ import annotations

from pathlib import Path

from app.exceptions import ImageLoadError
from app.models.audio import NarrationSegment
from app.models.video import ImageAsset
from app.utils.segment_namer import build_segment_basename

#: Supported image extensions, in deterministic priority order. When
#: more than one supported file exists for the same segment (e.g. both
#: a ``.png`` and a ``.jpg``), the first extension in this tuple that
#: matches an existing file is always chosen.
SUPPORTED_EXTENSIONS: tuple[str, ...] = ("png", "jpg", "jpeg", "webp")


def load_images_for_segments(
    image_dir: Path,
    segments: tuple[NarrationSegment, ...],
) -> tuple[ImageAsset, ...]:
    """Discover and match one image file per narration segment.

    For each segment, candidate filenames are computed for every
    extension in :data:`SUPPORTED_EXTENSIONS`, in order, using the
    shared ``"<index>_<label>"`` basename convention. The first
    candidate that exists on disk is selected.

    Args:
        image_dir: Directory expected to contain one image file per
            segment.
        segments: An ordered tuple of narration segments to find
            matching images for, in the order the resulting
            :class:`~app.models.video.ImageAsset` tuple should
            preserve.

    Returns:
        An ordered tuple of :class:`~app.models.video.ImageAsset`
        instances, one per input segment, in the same order as
        ``segments``.

    Raises:
        ImageLoadError: If ``image_dir`` does not exist, is not a
            directory, or if no supported image file can be found for
            any given segment.
    """
    if not image_dir.exists():
        raise ImageLoadError(f"Image directory not found: {image_dir}")

    if not image_dir.is_dir():
        raise ImageLoadError(f"Path is not a directory: {image_dir}")

    image_assets: list[ImageAsset] = []

    for segment in segments:
        matched_path = _find_image_for_segment(image_dir, segment)
        image_assets.append(ImageAsset(index=segment.index, file_path=matched_path))

    return tuple(image_assets)


def _find_image_for_segment(image_dir: Path, segment: NarrationSegment) -> Path:
    """Find the first existing supported image file for a single segment.

    Args:
        image_dir: Directory to search within.
        segment: The narration segment to find a matching image for.

    Returns:
        The path of the first matching image file found, checked in
        the extension priority order defined by
        :data:`SUPPORTED_EXTENSIONS`.

    Raises:
        ImageLoadError: If no supported image file exists for this
            segment.
    """
    basename = build_segment_basename(segment.index, segment.label)

    for extension in SUPPORTED_EXTENSIONS:
        candidate_path = image_dir / f"{basename}.{extension}"
        if candidate_path.is_file():
            return candidate_path

    supported = ", ".join(f".{ext}" for ext in SUPPORTED_EXTENSIONS)
    raise ImageLoadError(
        f"No image found for segment '{segment.label}' (index "
        f"{segment.index}) in directory '{image_dir}'. Expected a "
        f"file named like '{basename}.{SUPPORTED_EXTENSIONS[0]}' "
        f"with one of the supported extensions: {supported}."
    )

