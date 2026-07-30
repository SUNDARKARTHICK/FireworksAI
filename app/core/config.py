"""Configuration loading for the FireworksAI application.

This module is the single place in the codebase responsible for
reading configuration from the environment (and an optional ``.env``
file) and turning it into a validated :class:`~app.core.settings.Settings`
instance. No other module should read ``os.environ`` directly.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from app.core.settings import Settings
from app.exceptions import ConfigurationError

_VALID_LOG_LEVELS: frozenset[str] = frozenset(
    {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
)

_DEFAULTS: dict[str, str] = {
    "PROJECT_NAME": "FireworksAI",
    "VERSION": "0.1.0",
    "DEFAULT_LANGUAGE": "en",
    "DEFAULT_VOICE": "en-US-GuyNeural",
    "LOG_LEVEL": "INFO",
}


def _validate_non_empty(name: str, value: str) -> str:
    """Ensure a configuration value is a non-empty, stripped string.

    Args:
        name: The name of the configuration variable, used for error
            messages.
        value: The raw value to validate.

    Returns:
        The stripped, validated string value.

    Raises:
        ConfigurationError: If ``value`` is empty or only whitespace.
    """
    stripped = value.strip()
    if not stripped:
        raise ConfigurationError(f"Configuration value '{name}' must not be empty.")
    return stripped


def _validate_log_level(value: str) -> str:
    """Ensure a log level string is one of the supported levels.

    Args:
        value: The raw log level string (case-insensitive).

    Returns:
        The normalized, upper-cased log level string.

    Raises:
        ConfigurationError: If ``value`` is not a recognized log level.
    """
    normalized = value.strip().upper()
    if normalized not in _VALID_LOG_LEVELS:
        valid = ", ".join(sorted(_VALID_LOG_LEVELS))
        raise ConfigurationError(
            f"Invalid LOG_LEVEL '{value}'. Must be one of: {valid}."
        )
    return normalized


def load_settings(
    env_file: Path | None = None,
    base_dir: Path | None = None,
) -> Settings:
    """Load, validate, and return application settings.

    Reads configuration from environment variables, optionally
    preloaded from a ``.env`` file, falling back to sensible defaults
    for any value that is not set.

    Args:
        env_file: Optional path to a ``.env`` file to load before
            reading environment variables. If ``None``, ``python-dotenv``
            searches for a ``.env`` file starting from the current
            working directory. If the path does not exist, it is
            silently ignored and defaults/environment variables are
            used instead.
        base_dir: Root directory used to derive project directory
            paths. Defaults to the current working directory.

    Returns:
        A fully validated :class:`~app.core.settings.Settings` instance.

    Raises:
        ConfigurationError: If any configuration value fails validation.
    """
    if env_file is not None and env_file.exists():
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()

    resolved_base_dir = (base_dir or Path.cwd()).resolve()

    try:
        project_name = _validate_non_empty(
            "PROJECT_NAME", os.environ.get("PROJECT_NAME", _DEFAULTS["PROJECT_NAME"])
        )
        version = _validate_non_empty(
            "VERSION", os.environ.get("VERSION", _DEFAULTS["VERSION"])
        )
        default_language = _validate_non_empty(
            "DEFAULT_LANGUAGE",
            os.environ.get("DEFAULT_LANGUAGE", _DEFAULTS["DEFAULT_LANGUAGE"]),
        )
        default_voice = _validate_non_empty(
            "DEFAULT_VOICE",
            os.environ.get("DEFAULT_VOICE", _DEFAULTS["DEFAULT_VOICE"]),
        )
        log_level = _validate_log_level(
            os.environ.get("LOG_LEVEL", _DEFAULTS["LOG_LEVEL"])
        )
    except ConfigurationError:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        raise ConfigurationError(f"Failed to load configuration: {exc}") from exc

    return Settings(
        project_name=project_name,
        version=version,
        default_language=default_language,
        default_voice=default_voice,
        log_level=log_level,
        base_dir=resolved_base_dir,
    )
