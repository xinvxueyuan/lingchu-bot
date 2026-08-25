"""lc doctor — run environment diagnostics and report the result."""

from __future__ import annotations

import json

from rich.table import Table
import typer

from lingc_cli.console import get_console
from lingc_cli.core.meta import project_root
from lingc_cli.handlers.doctor import has_missing, run_checks
from lingc_cli.i18n import _

MISSING_EXIT_CODE = 3

_STATUS_STYLE = {"ok": "green", "warning": "yellow", "missing": "red"}


def register(app: typer.Typer) -> None:
    """Register the `doctor` subcommand onto the application."""

    @app.command("doctor", help=_("Run environment diagnostics."))
    def doctor(
        json_output: bool = typer.Option(
            False, "--json", help=_("Output the checks as JSON.")
        ),
    ) -> None:
        """Check the environment and exit with code 3 if anything is missing."""
        root = project_root()
        checks = run_checks(root)
        if json_output:
            payload = [
                {
                    "name": check.name,
                    "status": check.status,
                    "detail": check.detail,
                    "advice": check.advice,
                }
                for check in checks
            ]
            typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            table = Table(title=_("Diagnostics"))
            table.add_column(_("Check"), style="cyan", no_wrap=True)
            table.add_column(_("Status"))
            table.add_column(_("Detail"))
            table.add_column(_("Advice"))
            for check in checks:
                table.add_row(
                    check.name,
                    check.status,
                    check.detail,
                    check.advice,
                    style=_STATUS_STYLE.get(check.status, ""),
                )
            get_console().print(table)
        if has_missing(checks):
            raise typer.Exit(code=MISSING_EXIT_CODE)


__all__ = ["register"]
