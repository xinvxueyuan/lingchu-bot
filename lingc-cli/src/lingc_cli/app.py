"""Root Typer application for Lingc CLI."""

from __future__ import annotations

import typer

from lingc_cli import __version__
from lingc_cli.commands import add_all
from lingc_cli.core import config

app = typer.Typer(
    help="Lingchu Bot runtime launcher (game-launcher style runtime shell).",
    add_completion=False,
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True, no_args_is_help=True)
def _cli(
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version and exit."
    ),
    cwd: str | None = typer.Option(None, "-d", "--cwd", help="Working directory."),
    python: str | None = typer.Option(
        None, "--python", "-py", help="Python executable path."
    ),
    use_venv: bool = typer.Option(
        True, "--venv/--no-venv", help="Auto detect virtual environment."
    ),
) -> None:
    """Lingchu Bot runtime launcher."""
    if version:
        typer.echo(f"lc: lingc cli version {__version__}")
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
