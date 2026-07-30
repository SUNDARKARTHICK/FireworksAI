"""Application settings data model.

This module defines the :class:`Settings` dataclass, an immutable
container describing every configurable value the application needs.
It contains no I/O and no business logic: it does not read environment
variables, files, or the filesystem beyond representing paths. That
responsibility belongs to :mod:`app.core.config`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable application settings.

    Attributes:
        project_name: Human-readable name of the project.
        version: Semantic version string of the application.
        default_language: Default ISO language code used for content
            generation (e.g. ``"en"``).
        default_voice: Default text-to-speech voice identifier.
        log_level: Logging verbosity level name (e.g. ``"INFO"``).
        base_dir: Root directory of the project on disk.
        content_dir: Directory containing generated content assets.
        audio_dir: Directory containing generated audio files.
        subtitles_dir: Directory containing generated subtitle files.
        assets_dir: Directory containing static/generated assets.
        output_dir: Directory containing final rendered output.
        docs_dir: Directory containing project documentation.
    """

    project_name: str
    version: str
    default_language: str
    default_voice: str
    log_level: str
    base_dir: Path
    content_dir: Path = field(init=False)
    audio_dir: Path = field(init=False)
    subtitles_dir: Path = field(init=False)
    assets_dir: Path = field(init=False)
    output_dir: Path = field(init=False)
    docs_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        """Derive dependent directory paths from ``base_dir``.

        Uses ``object.__setattr__`` because the dataclass is frozen;
        this is the standard, safe pattern for computing derived
        fields on an immutable dataclass.
        """
        object.__setattr__(self, "content_dir", self.base_dir / "content")
        object.__setattr__(self, "audio_dir", self.base_dir / "content" / "audio")
        object.__setattr__(
            self, "subtitles_dir", self.base_dir / "content" / "subtitles"
        )
        object.__setattr__(self, "assets_dir", self.base_dir / "content" / "assets")
        object.__setattr__(self, "output_dir", self.base_dir / "output")
        object.__setattr__(self, "docs_dir", self.base_dir / "docs")
