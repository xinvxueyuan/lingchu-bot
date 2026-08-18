"""``lc run`` command: safely start and supervise the bot."""

from __future__ import annotations

import asyncio

import typer

from lingc_cli.consts import DEFAULT_STARTUP_TIMEOUT
from lingc_cli.core import config
from lingc_cli.exceptions import LingcCliError
from lingc_cli.handlers.run import run as run_handler
from lingc_cli.i18n import _


def register(app: typer.Typer) -> None:
    """Register the ``run`` subcommand onto *app*."""

    @app.command(help=_("Start the bot safely and supervise it until exit."))
    def run(
        reload: bool = typer.Option(
            False,
            "--reload",
            "-r",
            help=_("Restart the bot whenever its files change."),
        ),
        timeout: int = typer.Option(
            DEFAULT_STARTUP_TIMEOUT,
            "--timeout",
            help=_("Seconds to wait for the bot to finish starting."),
        ),
    ) -> None:
        """Start the bot safely and supervise it until it exits."""
        try:
            exit_code = asyncio.run(
                run_handler(
                    cmd=[],
                    cwd=config.get_cwd(),
                    timeout=timeout,
                    reload=reload,
                )
            )
        except LingcCliError as exc:
            typer.echo(_("Error: {message}").format(message=exc), err=True)
            raise typer.Exit(1) from exc
        raise typer.Exit(exit_code)
