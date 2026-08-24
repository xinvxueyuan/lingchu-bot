"""Rich console helpers for Lingc CLI output.

A fresh :class:`rich.console.Console` is created per call so it binds to the
``sys.stdout``/``sys.stderr`` in effect at print time (required for
``typer.testing.CliRunner`` to capture output).
"""

from __future__ import annotations

from rich.console import Console


def get_console(*, stderr: bool = False) -> Console:
    """Return a Rich console bound to stdout (or stderr when *stderr*)."""
    return Console(stderr=stderr)


__all__ = ["get_console"]
