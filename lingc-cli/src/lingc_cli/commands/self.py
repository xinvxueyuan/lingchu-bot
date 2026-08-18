"""lc self-update — upgrade the lingc-cli launcher itself."""

from __future__ import annotations

import anyio
import typer

from lingc_cli.exceptions import LingcCliError
from lingc_cli.handlers import self as self_handler
from lingc_cli.i18n import _


def register(app: typer.Typer) -> None:
    """Register the self-update subcommand onto the application."""

    @app.command("self-update", help=_("Upgrade the lingc-cli launcher itself."))
    def self_update() -> None:
        """Upgrade lingc-cli via uv tool, pipx, or manual instructions."""
        try:
            method = anyio.run(self_handler.self_update)
        except LingcCliError as exc:
            typer.echo(_("error: {message}").format(message=exc), err=True)
            raise typer.Exit(1) from exc
        if method == "manual":
            typer.echo(_("Could not detect uv or pipx; upgrade lingc-cli manually."))
        else:
            typer.echo(_("upgraded lingc-cli via {method}").format(method=method))


__all__ = ["register"]
