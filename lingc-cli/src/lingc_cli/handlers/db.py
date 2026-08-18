"""Database migration dispatch for Lingc CLI (lc db).

Wraps the installed nonebot-plugin-orm command-line so the launcher can drive
Alembic migrations (upgrade / check / revision / sync) with normalized exit
codes. The orm module is imported lazily so an unconfigured environment can
be reported cleanly as EnvironmentNotReadyError.
"""

from __future__ import annotations

import importlib

from lingc_cli.exceptions import EnvironmentNotReadyError
from lingc_cli.i18n import _


def _exit_code(result: object) -> int:
    """Normalize a click standalone-mode return value to an exit code."""
    if isinstance(result, int):
        return result
    return 0


def _error_exit_code(error: BaseException) -> int:
    """Normalize a raised click exception to a process exit code."""
    exit_code = getattr(error, "exit_code", None)
    if isinstance(exit_code, int):
        return exit_code
    return 1


def run_db(args: list[str]) -> int:
    """Run an orm subcommand and return its normalized exit code.

    Args:
        args: The orm subcommand and its arguments, e.g. ["upgrade"].

    Returns:
        The process exit code (0 on success).

    Raises:
        EnvironmentNotReadyError: If nonebot-plugin-orm is not installed.
    """
    try:
        orm_main = importlib.import_module("nonebot_plugin_orm.__main__")
    except ImportError as exc:
        raise EnvironmentNotReadyError(
            _("nonebot-plugin-orm is not installed; cannot run database commands.")
        ) from exc

    try:
        result = orm_main.main(args, prog_name="lc db", standalone_mode=False)
    except Exception as exc:
        return _error_exit_code(exc)
    return _exit_code(result)


__all__ = ["run_db"]
