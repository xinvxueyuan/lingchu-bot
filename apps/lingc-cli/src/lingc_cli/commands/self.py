"""lc self-update — upgrade lingc-cli itself."""

from __future__ import annotations

import anyio
import typer

from lingc_cli.console import get_console
from lingc_cli.exceptions import LingcCliError
from lingc_cli.handlers import self as self_handler
from lingc_cli.i18n import _


def register(app: typer.Typer) -> None:
    """Register the self-update subcommand onto the application."""

    @app.command("self-update", help=_("Upgrade lingc-cli itself."))
    def self_update() -> None:
        """Upgrade lingc-cli via uv tool, pipx, or manual instructions."""
        try:
            method = anyio.run(self_handler.self_update)
        except LingcCliError as exc:
            get_console(stderr=True).print(
                _("error: {message}").format(message=exc),
                style="bold red",
                markup=False,
            )
            raise typer.Exit(1) from exc
        if method == "manual":
            get_console().print(
                _("Could not detect uv or pipx; upgrade lingc-cli manually."),
                style="yellow",
                markup=False,
            )
        else:
            get_console().print(
                _("upgraded lingc-cli via {method}").format(method=method),
                style="green",
                markup=False,
            )


__all__ = ["register"]
