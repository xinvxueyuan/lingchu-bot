"""Domain exceptions for Lingc CLI."""

from __future__ import annotations


class LingcCliError(Exception):
    """Base class for all Lingc CLI errors."""


class EnvironmentNotReadyError(LingcCliError):
    """Raised when the target environment is not ready to run or manage."""


class ProcessExecutionError(LingcCliError):
    """Raised when a spawned subprocess exits with a non-zero status."""

    def __init__(self, message: str, *, exit_code: int | None = None) -> None:
        super().__init__(message)
        self.exit_code = exit_code
