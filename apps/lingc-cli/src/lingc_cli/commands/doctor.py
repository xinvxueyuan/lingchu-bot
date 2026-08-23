"""lc doctor — run environment diagnostics and report the result."""

from __future__ import annotations

import json

import typer

from lingc_cli.core.meta import project_root
from lingc_cli.handlers.doctor import has_missing, run_checks
from lingc_cli.i18n import _

MISSING_EXIT_CODE = 3


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
            for check in checks:
                typer.echo(f"{check.name}: {check.status} — {check.detail}")
                if check.advice:
                    typer.echo(f"  advice: {check.advice}")
        if has_missing(checks):
            raise typer.Exit(code=MISSING_EXIT_CODE)


__all__ = ["register"]
