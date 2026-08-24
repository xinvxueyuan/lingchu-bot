"""Command registration for Lingc CLI.

Each command module exposes a ``register(app)`` function; ``add_all`` wires them
onto the root application so ``lc`` exposes every subcommand.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lingc_cli.commands import (
    db,
    doctor,
    env,
    init,
    lifecycle,
    run as run_cmd,
    self as self_cmd,
)

if TYPE_CHECKING:
    import typer


def add_all(app: typer.Typer) -> None:
    """Register every command module onto the root application."""
    env.register(app)
    doctor.register(app)
    init.register(app)
    run_cmd.register(app)
    lifecycle.register(app)
    db.register(app)
    self_cmd.register(app)


__all__ = ["add_all"]
