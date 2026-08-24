"""Translate Typer's built-in help strings.

Typer hardcodes several user-facing help strings in English: the completion
options (``--install-completion`` / ``--show-completion``), the ``--help``
option, and the rich help panel titles. These are resolved lazily when the
Click command is built or help is rendered, so we patch the relevant Typer
internals to use the active locale.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import typer
import typer._click.decorators as _click_decorators
import typer._click.utils as _click_utils
import typer.completion as _typer_completion
import typer.rich_utils as _rich_utils

from lingc_cli.i18n import _

if TYPE_CHECKING:
    from collections.abc import Callable


def _install_completion_placeholder_function(
    install_completion: bool = typer.Option(
        None,
        "--install-completion",
        callback=_typer_completion.install_callback,
        expose_value=False,
        help=_("Install completion for the current shell."),
    ),
    show_completion: bool = typer.Option(
        None,
        "--show-completion",
        callback=_typer_completion.show_callback,
        expose_value=False,
        help=_(
            "Show completion for the current shell, to copy it or "
            "customize the installation."
        ),
    ),
) -> None:
    pass


def _install_completion_no_auto_placeholder_function(
    install_completion: _typer_completion.Shells = typer.Option(  # pyright: ignore[reportPrivateImportUsage]
        None,
        callback=_typer_completion.install_callback,
        expose_value=False,
        help=_("Install completion for the specified shell."),
    ),
    show_completion: _typer_completion.Shells = typer.Option(  # pyright: ignore[reportPrivateImportUsage]
        None,
        callback=_typer_completion.show_callback,
        expose_value=False,
        help=_(
            "Show completion for the specified shell, to copy it or "
            "customize the installation."
        ),
    ),
) -> None:
    pass


def _help_option(
    param_decls: list[str],
) -> Callable[
    [_click_decorators.Command], _click_decorators.Command  # pyright: ignore[reportPrivateImportUsage]
]:
    """Patched help option decorator with a translatable help string."""

    def show_help(
        ctx: _click_decorators.Context,  # pyright: ignore[reportPrivateImportUsage]
        _param: _click_decorators.Parameter,  # pyright: ignore[reportPrivateImportUsage]
        value: bool,
    ) -> None:
        if value and not ctx.resilient_parsing:
            _click_utils.echo(ctx.get_help(), color=ctx.color)
            ctx.exit()

    assert len(param_decls) > 0, "At least one help option should be provided"
    return _click_decorators.option(
        param_decls,
        is_flag=True,
        expose_value=False,
        is_eager=True,
        help=_("Show this message and exit."),
        callback=show_help,
        required=False,
    )


def apply() -> None:
    """Apply the Typer i18n patches (idempotent)."""
    _typer_completion._install_completion_placeholder_function = (
        _install_completion_placeholder_function
    )
    _typer_completion._install_completion_no_auto_placeholder_function = (
        _install_completion_no_auto_placeholder_function
    )
    _click_decorators.help_option = _help_option
    _rich_utils.ARGUMENTS_PANEL_TITLE = _("Arguments")
    _rich_utils.OPTIONS_PANEL_TITLE = _("Options")
    _rich_utils.COMMANDS_PANEL_TITLE = _("Commands")


__all__ = ["apply"]
