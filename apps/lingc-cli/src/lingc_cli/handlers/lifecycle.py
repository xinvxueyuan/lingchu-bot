"""Lifecycle management for Lingc CLI (lc install / uninstall / update / repair).

Installs and updates the Lingchu Bot plugin, pulls updates when the project
lives in a git checkout, and repairs missing environment pieces detected by
lc doctor. Never imports NoneBot or plugin internals.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING

from packaging.requirements import Requirement
import questionary

from lingc_cli.core.environment import (
    EnvironmentExecutor,
    PipEnvironmentExecutor,
    UvEnvironmentExecutor,
    probe_manager,
)
from lingc_cli.handlers.db import run_db
from lingc_cli.handlers.doctor import run_checks
from lingc_cli.handlers.env import package_version
from lingc_cli.handlers.init import init_project
from lingc_cli.i18n import _

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

DEFAULT_PACKAGE = "nonebot-plugin-lingchu-bot"

_DEPENDENCY_CHECKS = ("core", "adapters")


def get_executor(root: Path) -> EnvironmentExecutor:
    """Return the environment executor that matches the detected manager."""
    inferred, _ = probe_manager(root)
    if inferred == "uv":
        return UvEnvironmentExecutor(cwd=root)
    return PipEnvironmentExecutor(cwd=root)


def _to_requirements(packages: Sequence[str] | None) -> list[Requirement]:
    """Coerce package names into Requirement objects, defaulting the plugin."""
    names = list(packages) if packages else [DEFAULT_PACKAGE]
    return [Requirement(name) for name in names]


async def install(
    root: Path, packages: Sequence[str] | None = None
) -> list[Requirement]:
    """Install plugin dependencies into the project environment.

    When packages is omitted, installs the default Lingchu Bot plugin
    unless it is already present (idempotent). Returns the requirements that
    were actually installed.
    """
    requirements = _to_requirements(packages)
    if packages is None:
        requirements = [
            requirement
            for requirement in requirements
            if package_version(requirement.name) is None
        ]
        if not requirements:
            return []
    await get_executor(root).install(*requirements)
    return requirements


def _confirm_uninstall(requirements: Sequence[Requirement]) -> bool:
    """Ask the operator to confirm uninstalling the given packages."""
    names = ", ".join(requirement.name for requirement in requirements)
    return bool(
        questionary.confirm(
            _("Uninstall {packages}?").format(packages=names),
            default=False,
        ).ask()
    )


async def uninstall(
    root: Path, *, packages: Sequence[str] | None = None, yes: bool = False
) -> list[Requirement]:
    """Uninstall packages from the environment, confirming unless yes."""
    requirements = _to_requirements(packages)
    if not yes and not _confirm_uninstall(requirements):
        return []
    await get_executor(root).uninstall(*requirements)
    return requirements


async def _git_pull(root: Path) -> None:
    """Pull the latest commit for a git checkout."""
    process = await asyncio.create_subprocess_exec("git", "pull", cwd=root)
    await process.wait()


async def update(root: Path, *, yes: bool = False) -> None:
    """Pull a git checkout (best-effort) and update project dependencies."""
    del yes
    if (root / ".git").exists():
        with suppress(Exception):
            await _git_pull(root)
    await get_executor(root).update()


async def _repair_check(root: Path, name: str) -> str | None:
    """Apply the fix for a single missing check, returning its action label."""
    if name in _DEPENDENCY_CHECKS:
        await install(root)
        return "install"
    if name == "config":
        init_project(root)
        return "init"
    if name == "migration":
        run_db(["upgrade"])
        return "db upgrade"
    return None


async def repair(root: Path, *, yes: bool = False) -> list[str]:
    """Repair every missing doctor check and return the performed actions."""
    del yes
    actions: list[str] = []
    for check in run_checks(root):
        if check.status != "missing":
            continue
        if (action := await _repair_check(root, check.name)) is not None:
            actions.append(action)
    return actions


__all__ = [
    "DEFAULT_PACKAGE",
    "get_executor",
    "install",
    "repair",
    "uninstall",
    "update",
]
