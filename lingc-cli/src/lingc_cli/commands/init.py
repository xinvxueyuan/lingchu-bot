"""lc init — scaffold a minimal .env for a Lingchu Bot project."""

from __future__ import annotations

import typer

from lingc_cli.core.meta import project_root
from lingc_cli.handlers.init import init_project
from lingc_cli.i18n import _


def register(app: typer.Typer) -> None:
    """Register the `init` subcommand onto the application."""

    @app.command("init", help=_("Generate a minimal .env if missing."))
    def init(
        force: bool = typer.Option(
            False, "--force", help=_("Overwrite an existing .env.")
        ),
    ) -> None:
        """Scaffold the project environment file."""
        root = project_root()
        created = init_project(root, force=force)
        if not created:
            typer.echo(_(".env already exists (use --force to overwrite)."))
            return
        for path in created:
            typer.echo(f"generated: {path}")


__all__ = ["register"]
