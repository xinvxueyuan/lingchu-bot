"""Environment manager executor abstraction for Lingc CLI.

Mirrors the EnvironmentExecutor pattern from nb-cli handlers so project
packages can be installed / updated / uninstalled and the environment synced,
transparently backed by either uv or pip.
"""

from __future__ import annotations

import abc
import asyncio
from shutil import which
from typing import TYPE_CHECKING, override

from lingc_cli.core import meta
from lingc_cli.exceptions import ProcessExecutionError
from lingc_cli.i18n import _

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from packaging.requirements import Requirement

_MANAGER_FEATURES: dict[str, str] = {"uv": "uv.lock"}


def probe_manager(cwd: Path | None = None) -> tuple[str, str]:
    """Probe the manager inferred for, and usable by, the current project.

    Args:
        cwd: The directory from which the project-root lookup starts.

    Returns:
        A (inferred, available) tuple. inferred is decided by the
        presence of a uv.lock file (uv) or falls back to pip.
        available is inferred when the manager is on PATH, else pip.
    """
    root = meta.project_root(cwd)
    current = "uv" if (root / "uv.lock").exists() else "pip"
    available = current if which(current) is not None else "pip"
    return current, available


def all_managers() -> list[str]:
    """Return the environment managers available on this system.

    Returns:
        The detected manager names together with pip as an unconditional
        fallback.
    """
    return [*(name for name in _MANAGER_FEATURES if which(name) is not None), "pip"]


class EnvironmentExecutor(metaclass=abc.ABCMeta):
    """Abstract base class for environment executors."""

    cwd: Path
    executable: str

    def __init__(self, *, cwd: Path, executable: str) -> None:
        self.cwd = cwd
        self.executable = executable

    async def _spawn(self, *args: str) -> int:
        """Run the executable with args in the project directory.

        Args:
            args: Extra command-line arguments for the subprocess.

        Returns:
            The subprocess exit code.
        """
        process = await asyncio.create_subprocess_exec(
            self.executable, *args, cwd=self.cwd
        )
        return await process.wait()

    @abc.abstractmethod
    async def sync(self, extra_args: Sequence[str] = ()) -> None:
        """Synchronize the environment with the lock file or configuration."""

    @abc.abstractmethod
    async def install(
        self, *packages: Requirement, extra_args: Sequence[str] = (), dev: bool = False
    ) -> None:
        """Install packages into the environment."""

    @abc.abstractmethod
    async def update(
        self, *packages: Requirement, extra_args: Sequence[str] = ()
    ) -> None:
        """Update packages (or, when empty, everything) in the environment."""

    @abc.abstractmethod
    async def uninstall(
        self, *packages: Requirement, extra_args: Sequence[str] = ()
    ) -> None:
        """Uninstall packages from the environment."""


class UvEnvironmentExecutor(EnvironmentExecutor):
    """Environment executor for the uv manager."""

    def __init__(self, *, cwd: Path, executable: str | None = None) -> None:
        super().__init__(cwd=cwd, executable=executable or which("uv") or "uv")

    @override
    async def sync(self, extra_args: Sequence[str] = ()) -> None:
        if await self._spawn("sync", *extra_args) != 0:
            raise ProcessExecutionError(_("Failed to sync uv environment."))

    @override
    async def install(
        self, *packages: Requirement, extra_args: Sequence[str] = (), dev: bool = False
    ) -> None:
        command = (*extra_args, "--dev") if dev else extra_args
        if await self._spawn("add", *(str(pkg) for pkg in packages), *command) != 0:
            raise ProcessExecutionError(
                _("Failed to install packages in uv environment.")
            )

    @override
    async def update(
        self, *packages: Requirement, extra_args: Sequence[str] = ()
    ) -> None:
        if (
            await self._spawn(
                "add", "--upgrade", *(str(pkg) for pkg in packages), *extra_args
            )
            != 0
        ):
            raise ProcessExecutionError(
                _("Failed to update packages in uv environment.")
            )

    @override
    async def uninstall(
        self, *packages: Requirement, extra_args: Sequence[str] = ()
    ) -> None:
        if (
            await self._spawn("remove", *(str(pkg) for pkg in packages), *extra_args)
            != 0
        ):
            raise ProcessExecutionError(
                _("Failed to uninstall packages from uv environment.")
            )


class PipEnvironmentExecutor(EnvironmentExecutor):
    """Environment executor for the pip manager, driven by the resolved Python."""

    def __init__(self, *, cwd: Path, executable: str | None = None) -> None:
        super().__init__(cwd=cwd, executable=executable or meta.resolve_python(cwd))

    @override
    async def sync(self, extra_args: Sequence[str] = ()) -> None:
        if await self._spawn("-m", "pip", "install", "-e", ".", *extra_args) != 0:
            raise ProcessExecutionError(_("Failed to sync pip environment."))

    @override
    async def install(
        self, *packages: Requirement, extra_args: Sequence[str] = (), dev: bool = False
    ) -> None:
        # pip has no project-group concept; dev is accepted for interface parity.
        del dev
        if (
            await self._spawn(
                "-m", "pip", "install", *(str(pkg) for pkg in packages), *extra_args
            )
            != 0
        ):
            raise ProcessExecutionError(
                _("Failed to install packages in pip environment.")
            )

    @override
    async def update(
        self, *packages: Requirement, extra_args: Sequence[str] = ()
    ) -> None:
        if (
            await self._spawn(
                "-m",
                "pip",
                "install",
                "--upgrade",
                *(str(pkg) for pkg in packages),
                *extra_args,
            )
            != 0
        ):
            raise ProcessExecutionError(
                _("Failed to update packages in pip environment.")
            )

    @override
    async def uninstall(
        self, *packages: Requirement, extra_args: Sequence[str] = ()
    ) -> None:
        if (
            await self._spawn(
                "-m", "pip", "uninstall", *(str(pkg) for pkg in packages), *extra_args
            )
            != 0
        ):
            raise ProcessExecutionError(
                _("Failed to uninstall packages from pip environment.")
            )


__all__ = [
    "EnvironmentExecutor",
    "PipEnvironmentExecutor",
    "UvEnvironmentExecutor",
    "all_managers",
    "probe_manager",
]
