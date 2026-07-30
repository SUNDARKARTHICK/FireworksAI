"""Unit tests for Milestone 1: configuration, logging, and workflow.

These tests verify:
    * Configuration loads successfully with defaults and with
      environment overrides, and rejects invalid values.
    * The logger initializes with console and file handlers.
    * The workflow initializes and returns a successful result.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from app.core.config import load_settings
from app.core.logging_config import configure_logging
from app.core.settings import Settings
from app.exceptions import ConfigurationError, PipelineError
from app.pipeline.workflow import WorkflowResult, run_workflow


class TestLoadSettings:
    """Tests for :func:`app.core.config.load_settings`."""

    def test_loads_defaults_when_no_env_vars_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Configuration loads successfully using default values."""
        for var in (
            "PROJECT_NAME",
            "VERSION",
            "DEFAULT_LANGUAGE",
            "DEFAULT_VOICE",
            "LOG_LEVEL",
        ):
            monkeypatch.delenv(var, raising=False)

        missing_env_file = tmp_path / "does_not_exist.env"
        settings = load_settings(env_file=missing_env_file, base_dir=tmp_path)

        assert settings.project_name == "FireworksAI"
        assert settings.version == "0.1.0"
        assert settings.default_language == "en"
        assert settings.default_voice == "en-US-GuyNeural"
        assert settings.log_level == "INFO"

    def test_loads_overridden_env_vars(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Configuration respects environment variable overrides."""
        monkeypatch.setenv("PROJECT_NAME", "CustomProject")
        monkeypatch.setenv("VERSION", "9.9.9")
        monkeypatch.setenv("DEFAULT_LANGUAGE", "fr")
        monkeypatch.setenv("DEFAULT_VOICE", "fr-FR-HenriNeural")
        monkeypatch.setenv("LOG_LEVEL", "debug")

        settings = load_settings(base_dir=tmp_path)

        assert settings.project_name == "CustomProject"
        assert settings.version == "9.9.9"
        assert settings.default_language == "fr"
        assert settings.default_voice == "fr-FR-HenriNeural"
        assert settings.log_level == "DEBUG"

    def test_derives_directory_paths_from_base_dir(self, tmp_path: Path) -> None:
        """Derived directory paths are correctly rooted at base_dir."""
        settings = load_settings(base_dir=tmp_path)

        assert settings.content_dir == tmp_path / "content"
        assert settings.audio_dir == tmp_path / "content" / "audio"
        assert settings.subtitles_dir == tmp_path / "content" / "subtitles"
        assert settings.assets_dir == tmp_path / "content" / "assets"
        assert settings.output_dir == tmp_path / "output"
        assert settings.docs_dir == tmp_path / "docs"

    def test_invalid_log_level_raises_configuration_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An invalid LOG_LEVEL raises ConfigurationError."""
        monkeypatch.setenv("LOG_LEVEL", "NOT_A_LEVEL")

        with pytest.raises(ConfigurationError):
            load_settings(base_dir=tmp_path)

    def test_empty_project_name_raises_configuration_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An empty PROJECT_NAME raises ConfigurationError."""
        monkeypatch.setenv("PROJECT_NAME", "   ")

        with pytest.raises(ConfigurationError):
            load_settings(base_dir=tmp_path)


class TestConfigureLogging:
    """Tests for :func:`app.core.logging_config.configure_logging`."""

    def _make_settings(self, tmp_path: Path, log_level: str = "INFO") -> Settings:
        return Settings(
            project_name="TestProject",
            version="0.0.1",
            default_language="en",
            default_voice="en-US-GuyNeural",
            log_level=log_level,
            base_dir=tmp_path,
        )

    def test_logger_initializes_with_expected_level(self, tmp_path: Path) -> None:
        """Logger initializes and is set to the configured log level."""
        settings = self._make_settings(tmp_path, log_level="DEBUG")

        logger = configure_logging(settings)

        assert logger.level == logging.DEBUG
        assert logger.name == "fireworksai"

    def test_logger_has_console_and_file_handlers(self, tmp_path: Path) -> None:
        """Logger is configured with both console and file handlers."""
        settings = self._make_settings(tmp_path)

        logger = configure_logging(settings)

        handler_types = {type(handler).__name__ for handler in logger.handlers}
        assert "StreamHandler" in handler_types
        assert "RotatingFileHandler" in handler_types

    def test_log_file_is_created_on_disk(self, tmp_path: Path) -> None:
        """Configuring logging creates the log file under output_dir."""
        settings = self._make_settings(tmp_path)

        logger = configure_logging(settings)
        logger.info("test message")
        for handler in logger.handlers:
            handler.flush()

        expected_log_file = settings.output_dir / "logs" / "fireworksai.log"
        assert expected_log_file.exists()

    def test_configure_logging_is_idempotent(self, tmp_path: Path) -> None:
        """Calling configure_logging twice does not duplicate handlers."""
        settings = self._make_settings(tmp_path)

        configure_logging(settings)
        logger = configure_logging(settings)

        assert len(logger.handlers) == 2


class TestRunWorkflow:
    """Tests for :func:`app.pipeline.workflow.run_workflow`."""

    def _make_settings(self, tmp_path: Path) -> Settings:
        return Settings(
            project_name="TestProject",
            version="0.0.1",
            default_language="en",
            default_voice="en-US-GuyNeural",
            log_level="INFO",
            base_dir=tmp_path,
        )

    def test_workflow_initializes_successfully_with_injected_settings(
        self, tmp_path: Path
    ) -> None:
        """Workflow returns a successful result when given valid settings."""
        settings = self._make_settings(tmp_path)

        result = run_workflow(settings=settings)

        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.settings is settings
        assert "successfully" in result.message.lower()

    def test_workflow_uses_injected_logger(self, tmp_path: Path) -> None:
        """Workflow uses an injected logger instead of creating a new one."""
        settings = self._make_settings(tmp_path)
        fake_logger = logging.getLogger("fireworksai.test.injected")
        fake_logger.handlers.clear()
        records: list[logging.LogRecord] = []

        class ListHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        fake_logger.addHandler(ListHandler())
        fake_logger.setLevel(logging.INFO)

        result = run_workflow(settings=settings, logger=fake_logger)

        assert result.success is True
        assert any("Workflow initialized" in r.getMessage() for r in records)

    def test_workflow_loads_real_settings_when_none_injected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Workflow loads settings via load_settings when none are injected."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("PROJECT_NAME", raising=False)

        result = run_workflow()

        assert result.success is True
        assert result.settings.project_name == "FireworksAI"

    def test_workflow_wraps_settings_failure_in_pipeline_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A settings-loading failure is wrapped in a PipelineError."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("LOG_LEVEL", "INVALID_LEVEL")

        with pytest.raises(PipelineError):
            run_workflow()
