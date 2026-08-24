"""Root Typer application for Lingc CLI."""

from __future__ import annotations

import typer

from lingc_cli import __version__
from lingc_cli._typer_i18n import apply as _apply_typer_i18n
from lingc_cli.commands import add_all
from lingc_cli.console import get_console
from lingc_cli.core import config
from lingc_cli.i18n import _

_apply_typer_i18n()

app = typer.Typer(
    help=_(
        "A convenience command-line tool for operating and maintaining Lingchu Bot."
    ),
    add_completion=True,
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True, no_args_is_help=True)
def _cli(
    version: bool = typer.Option(
        False, "--version", "-V", help=_("Show version and exit.")
    ),
    cwd: str | None = typer.Option(None, "-d", "--cwd", help=_("Working directory.")),
    python: str | None = typer.Option(
        None, "--python", "-py", help=_("Python executable path.")
    ),
    use_venv: bool = typer.Option(
        True, "--venv/--no-venv", help=_("Auto detect virtual environment.")
    ),
) -> None:
    """A convenience command-line tool for operating and maintaining Lingchu Bot."""
    if version:
        get_console().print(
            f"lc: lingc cli version {__version__}", style="bold", markup=False
        )
        raise typer.Exit
    if cwd is not None:
        config.set_cwd(cwd)
    if python is not None:
        config.set_python(python)
    config.set_use_venv(use_venv)


add_all(app)


def main() -> None:
    """Console entry point for the `lc` command."""
    app()


__all__ = ["app", "main"]
