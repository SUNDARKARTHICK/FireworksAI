"""
TTS Service

Purpose:
    This service communicates with Microsoft Edge TTS to generate audio.

Responsibilities:
    - Receive narration text
    - Receive voice configuration
    - Receive output path
    - Generate an MP3 file
    - Return an Audio object

This service does NOT:
    - Parse Markdown
    - Read files
    - Coordinate pipeline logic
"""