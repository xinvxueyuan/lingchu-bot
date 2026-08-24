"""lc env — print a snapshot of the current environment."""

from __future__ import annotations

import json
from typing import cast

from rich.table import Table
import typer

from lingc_cli.console import get_console
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
        table = Table(title=_("Environment snapshot"))
        table.add_column(_("Key"), style="cyan", no_wrap=True)
        table.add_column(_("Value"))
        table.add_row(_("OS"), str(snapshot["os"]))
        table.add_row(
            _("Python"),
            f"{snapshot['python_version']} ({snapshot['python_path']})",
        )
        table.add_row(_("uv / pip"), f"{snapshot['uv']} | {snapshot['pip']}")
        table.add_row(_("venv"), str(snapshot["venv"]))
        adapters = cast("list[dict[str, str]]", snapshot["adapters"])
        if adapters:
            table.add_row(
                _("adapters"),
                ", ".join(
                    f"{adapter['name']} {adapter['version']}" for adapter in adapters
                ),
            )
        else:
            table.add_row(_("adapters"), _("(none)"))
        lingchu = snapshot["lingchu_bot_version"]
        table.add_row(
            "nonebot-plugin-lingchu-bot",
            str(lingchu or _("(not installed)")),
        )
        table.add_row(_("project root"), str(snapshot["project_root"]))
        get_console().print(table)


__all__ = ["register"]
