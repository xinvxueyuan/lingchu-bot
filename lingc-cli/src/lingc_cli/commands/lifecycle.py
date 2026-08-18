"""lc install / uninstall / update / repair — manage the plugin lifecycle."""

from __future__ import annotations

import anyio
import typer

from lingc_cli.core.meta import project_root
from lingc_cli.exceptions import LingcCliError
from lingc_cli.handlers import lifecycle
from lingc_cli.i18n import _


def _abort(error: LingcCliError) -> None:
    """Print an error and exit with a non-zero status."""
    typer.echo(_("error: {message}").format(message=error), err=True)
    raise typer.Exit(1) from error


def register(app: typer.Typer) -> None:
    """Register the lifecycle subcommands onto the application."""

    @app.command("install", help=_("Install the Lingchu Bot plugin or extra packages."))
    def install(
        packages: list[str] | None = typer.Option(
            None, "--package", "-p", help="Package to install (repeatable)."
        ),
    ) -> None:
        """Install plugin dependencies into the project environment."""
        try:
            installed = anyio.run(lifecycle.install, project_root(), packages)
        except LingcCliError as exc:
            _abort(exc)
        if installed:
            names = ", ".join(requirement.name for requirement in installed)
            typer.echo(_("installed: {packages}").format(packages=names))
        else:
            typer.echo(_("nothing to install (already present)."))

    @app.command("uninstall", help=_("Uninstall Lingchu Bot plugin or extra packages."))
    def uninstall(
        packages: list[str] | None = typer.Option(
            None, "--package", "-p", help="Package to uninstall (repeatable)."
        ),
        yes: bool = typer.Option(
            False, "--yes", help=_("Skip the confirmation prompt.")
        ),
    ) -> None:
        """Uninstall packages, prompting for confirmation unless --yes."""
        try:
            removed = anyio.run(
                lambda: lifecycle.uninstall(project_root(), packages=packages, yes=yes)
            )
        except LingcCliError as exc:
            _abort(exc)
        if not removed:
            typer.echo(_("nothing uninstalled."))
            return
        names = ", ".join(requirement.name for requirement in removed)
        typer.echo(_("uninstalled: {packages}").format(packages=names))

    @app.command("update", help=_("Pull git changes and update dependencies."))
    def update(
        yes: bool = typer.Option(
            False, "--yes", help=_("Skip the confirmation prompt.")
        ),
    ) -> None:
        """Refresh the checkout and the installed dependencies."""
        try:
            anyio.run(lambda: lifecycle.update(project_root(), yes=yes))
        except LingcCliError as exc:
            _abort(exc)
        typer.echo(_("updated."))

    @app.command("repair", help=_("Repair missing pieces detected by lc doctor."))
    def repair(
        yes: bool = typer.Option(
            False, "--yes", help=_("Skip the confirmation prompt.")
        ),
    ) -> None:
        """Fix every missing doctor check and report the performed actions."""
        try:
            actions = anyio.run(lambda: lifecycle.repair(project_root(), yes=yes))
        except LingcCliError as exc:
            _abort(exc)
        if not actions:
            typer.echo(_("nothing to repair."))
            return
        typer.echo(_("repaired: {actions}").format(actions=", ".join(actions)))


__all__ = ["register"]
