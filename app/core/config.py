"""Configuration management for the FireworksAI application.

This module centralizes environment-based settings and ensures paths are
normalized for use across the project.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final


@dataclass(frozen=True)
class Settings:
    """Application configuration values loaded from environment variables.

    Notes:
        - output_dir and assets_dir are explicit to support Milestone 4
          video pipeline behaviour.
    """

    project_name: str
    app_env: str
    log_level: str
    output_dir: Path
    assets_dir: Path


def load_settings() -> Settings:
    """Load application settings from environment variables.

    Environment variables are read from the process environment and default
    values are provided so the app can run in local development without a
    custom configuration file.
    """

    project_root = Path(__file__).resolve().parent.parent.parent

    output_dir = Path(
        os.getenv("FIREWORKSAI_OUTPUT_DIR", str(project_root / "output"))
    ).expanduser().resolve()

    assets_dir = Path(
        os.getenv("FIREWORKSAI_ASSETS_DIR", str(project_root / "assets"))
    ).expanduser().resolve()

    return Settings(
        project_name=os.getenv("FIREWORKSAI_PROJECT_NAME", "FireworksAI"),
        app_env=os.getenv("FIREWORKSAI_ENV", "development"),
        log_level=os.getenv("FIREWORKSAI_LOG_LEVEL", "INFO"),
        output_dir=output_dir,
        assets_dir=assets_dir,
    )
