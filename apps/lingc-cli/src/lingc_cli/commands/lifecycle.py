"""lc install / uninstall / update / repair — manage the plugin lifecycle."""

from __future__ import annotations

from typing import TYPE_CHECKING

import anyio
import typer

from lingc_cli.console import get_console
from lingc_cli.core.meta import project_root
from lingc_cli.exceptions import LingcCliError
from lingc_cli.handlers import lifecycle
from lingc_cli.i18n import _

if TYPE_CHECKING:
    from typing import NoReturn


def _abort(error: LingcCliError) -> NoReturn:
    """Print an error and exit with a non-zero status."""
    get_console(stderr=True).print(
        _("error: {message}").format(message=error), style="bold red", markup=False
    )
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
            get_console().print(
                _("installed: {packages}").format(packages=names),
                style="green",
                markup=False,
            )
        else:
            get_console().print(
                _("nothing to install (already present)."),
                style="yellow",
                markup=False,
            )

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
            get_console().print(_("nothing uninstalled."), style="yellow", markup=False)
            return
        names = ", ".join(requirement.name for requirement in removed)
        get_console().print(
            _("uninstalled: {packages}").format(packages=names),
            style="green",
            markup=False,
        )

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
        get_console().print(_("updated."), style="green", markup=False)

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
            get_console().print(_("nothing to repair."), style="yellow", markup=False)
            return
        get_console().print(
            _("repaired: {actions}").format(actions=", ".join(actions)),
            style="green",
            markup=False,
        )


__all__ = ["register"]
