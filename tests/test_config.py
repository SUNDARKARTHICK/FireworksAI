"""Tests for the core configuration loader."""

from pathlib import Path

from app.core.config import load_settings


def test_load_settings_reads_environment(monkeypatch, tmp_path) -> None:
    """Configuration should honor environment overrides and normalize paths."""
    monkeypatch.setenv("FIREWORKSAI_PROJECT_NAME", "FireworksAI")
    monkeypatch.setenv("FIREWORKSAI_ENV", "development")
    monkeypatch.setenv("FIREWORKSAI_LOG_LEVEL", "DEBUG")
    output_dir = tmp_path / "output"
    monkeypatch.setenv("FIREWORKSAI_OUTPUT_DIR", str(output_dir))

    settings = load_settings()

    assert settings.project_name == "FireworksAI"
    assert settings.app_env == "development"
    assert settings.log_level == "DEBUG"
    assert settings.output_dir == output_dir
