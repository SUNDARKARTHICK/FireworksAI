"""
Audio Model

Purpose:
    Represents a generated audio file.

Responsibilities:
    - Store filename
    - Store file path
    - Store format
    - Store duration
    - Store voice
    - Store language

This model does NOT:
    - Generate audio
    - Read files
    - Play audio
    - Use Edge TTS
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Audio:
    """
    Represents a generated audio file.

    Attributes:
        filename: Name of the audio file.
        file_path: Full path to the generated audio file.
        format: Audio format (e.g., mp3).
        duration: Duration of the audio in seconds.
        voice: Voice used for narration.
        language: Language of the narration.
    """

    filename: str
    file_path: Path
    format: str
    duration: float
    voice: str
    language: str