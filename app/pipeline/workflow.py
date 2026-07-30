"""Main workflow entry point for the FireworksAI application.

This module orchestrates the minimal Milestone 1 startup sequence:
load settings, configure logging, and report success. It contains no
domain/business logic — that is reserved for future milestones.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import load_settings
from app.core.logging_config import configure_logging
from app.core.settings import Settings
from app.exceptions import PipelineError

import logging


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    """Outcome of running the application workflow.

    Attributes:
        success: Whether the workflow completed without error.
        settings: The settings that were loaded during the run.
        message: A short human-readable status message.
    """

    success: bool
    settings: Settings
    message: str


def run_workflow(
    settings: Settings | None = None,
    logger: logging.Logger | None = None,
) -> WorkflowResult:
    """Run the Milestone 1 application workflow.

    Sequence:
        1. Load settings (if not injected).
        2. Configure the application logger (if not injected).
        3. Return a :class:`WorkflowResult` indicating success.

    Args:
        settings: Optional pre-built :class:`Settings` instance. If
            ``None``, settings are loaded via
            :func:`app.core.config.load_settings`. Injectable for
            testing.
        logger: Optional pre-configured logger. If ``None``, a logger
            is configured via
            :func:`app.core.logging_config.configure_logging`.
            Injectable for testing.

    Returns:
        A :class:`WorkflowResult` describing the outcome.

    Raises:
        PipelineError: If settings loading or logger configuration
            fails.
    """
    try:
        resolved_settings = settings if settings is not None else load_settings()
    except Exception as exc:
        raise PipelineError(f"Workflow failed to load settings: {exc}") from exc

    try:
        resolved_logger = (
            logger if logger is not None else configure_logging(resolved_settings)
        )
    except Exception as exc:
        raise PipelineError(f"Workflow failed to configure logging: {exc}") from exc

    resolved_logger.info(
        "Workflow initialized successfully for project '%s' v%s",
        resolved_settings.project_name,
        resolved_settings.version,
    )

    return WorkflowResult(
        success=True,
        settings=resolved_settings,
        message="Workflow initialized successfully.",
    )


if __name__ == "__main__":
    result = run_workflow()
    print(result.message)  # noqa: T201 - CLI entry point output, not app logging
