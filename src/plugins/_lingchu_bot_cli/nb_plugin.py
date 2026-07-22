"""Official nb-cli Click plugin delegating to the Typer module entry point."""

from __future__ import annotations

from importlib import import_module
import subprocess
import sys
from typing import NoReturn

import click


@click.command(
    name="lingchu",
    add_help_option=False,
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def lingchu(ctx: click.Context, args: tuple[str, ...]) -> NoReturn:
    """Run the Lingchu Typer CLI without preparing a NoneBot project."""
    completed = subprocess.run(
        (sys.executable, "-m", "_lingchu_bot_cli", *args),
        check=False,
    )
    ctx.exit(completed.returncode)


def install() -> None:
    """Register the Lingchu command on nb-cli's public Click group."""
    cli = import_module("nb_cli.cli").cli
    cli.add_command(lingchu)
