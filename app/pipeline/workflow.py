"""Workflow orchestration skeleton for FireworksAI.

This module defines the high-level flow for turning a Markdown script into a
video asset. The implementation is intentionally simple at this milestone and
will be expanded in later milestones.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings, load_settings
from app.core.logging_setup import setup_logging

logger = setup_logging()


class Workflow:
    """Coordinate the media generation pipeline."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the workflow with configuration and logging."""
        self.settings = settings or load_settings()
        self.logger = logger

    def run(self, script_path: str | Path) -> Path:
        """Run the pipeline for a single script.

        Args:
            script_path: Path to the markdown script to process.

        Returns:
            The output directory for the generated asset.
        """
        input_path = Path(script_path)
        output_dir = self.settings.output_dir / input_path.stem
        output_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info("Workflow started for %s", input_path)
        self.logger.info("Output directory: %s", output_dir)
        return output_dir
