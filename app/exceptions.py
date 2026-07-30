"""Custom exception types shared across the FireworksAI application.

This module intentionally contains only exception class declarations.
It has no external dependencies and no business logic, so it can be
safely imported from any layer of the application without introducing
circular imports or coupling.
"""

from __future__ import annotations


class FireworksAIError(Exception):
    """Base class for all FireworksAI application-specific errors.

    All custom exceptions in this project should inherit from this
    class so that calling code can catch a single base type when it
    only cares that *some* FireworksAI error occurred.
    """


class ConfigurationError(FireworksAIError):
    """Raised when application configuration is missing or invalid.

    Examples:
        Raised when a required environment variable is absent, or when
        a configuration value fails validation (e.g. an empty project
        name or an invalid log level).
    """


class PipelineError(FireworksAIError):
    """Raised when the workflow/pipeline fails to execute correctly.

    Examples:
        Raised when a pipeline stage cannot complete initialization or
        cannot hand off to the next stage.
    """


class ValidationError(FireworksAIError):
    """Raised when a value fails a validation check.

    Examples:
        Raised when user-supplied or environment-supplied data does
        not satisfy the constraints required by the application.
    """


class FileLoadError(FireworksAIError):
    """Raised when a source file cannot be safely loaded from disk.

    Examples:
        Raised when a Markdown file does not exist, is not a regular
        file, or cannot be read due to an OS-level error (e.g.
        permissions, encoding).
    """


class MarkdownParsingError(FireworksAIError):
    """Raised when Markdown content cannot be parsed into a Script.

    Examples:
        Raised when YAML front matter is missing or invalid, when
        required metadata fields are absent, or when the expected
        introduction/section/conclusion structure is not present.
    """
