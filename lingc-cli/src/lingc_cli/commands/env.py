"""lc env — print a snapshot of the current environment."""

from __future__ import annotations

import json

import typer

from lingc_cli.core.meta import project_root
from lingc_cli.handlers.env import env_snapshot
from lingc_cli.i18n import _


def register(app: typer.Typer) -> None:
    """Register the `env` subcommand onto the application."""

    @app.command("env", help=_("Print the runtime environment snapshot."))
    def env(
        json_output: bool = typer.Option(
            False, "--json", help=_("Output the snapshot as JSON.")
        ),
    ) -> None:
        """Show OS, Python, uv/pip, adapters, and plugin versions."""
        root = project_root()
        snapshot = env_snapshot(root)
        if json_output:
            typer.echo(json.dumps(snapshot, indent=2, ensure_ascii=False))
            raise typer.Exit
        typer.echo(f"os: {snapshot['os']}")
        typer.echo(f"python: {snapshot['python_version']} ({snapshot['python_path']})")
        typer.echo(f"uv: {snapshot['uv']} | pip: {snapshot['pip']}")
        typer.echo(f"venv: {snapshot['venv']}")
        adapters = snapshot["adapters"]
        if adapters:
            typer.echo("adapters:")
            for adapter in adapters:
                typer.echo(f"  - {adapter['name']} {adapter['version']}")
        else:
            typer.echo("adapters: (none)")
        lingchu = snapshot["lingchu_bot_version"]
        typer.echo(f"nonebot-plugin-lingchu-bot: {lingchu or _('(not installed)')}")
        typer.echo(f"project root: {snapshot['project_root']}")


__all__ = ["register"]
