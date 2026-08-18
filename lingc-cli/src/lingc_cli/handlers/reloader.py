"""File-watch based reloader that restarts a child process on change."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from watchfiles import awatch

from lingc_cli.i18n import _
from lingc_cli.log import get_logger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    import logging


class ReloaderError(Exception):
    """A child failed to complete startup (timeout or early exit).

    Carries the exit code the launcher should report so the reload loop can
    hand the failure back instead of pretending the bot started cleanly.
    """

    def __init__(self, exit_code: int) -> None:
        super().__init__(exit_code)
        self.exit_code = exit_code


class Reloader:
    """Restart a child process whenever a watched file changes.

    ``startup_func`` must return a *confirmed* running child (one that has
    already passed startup), while ``shutdown_func`` gracefully stops one.
    The watch loop restarts the child on every detected change and stops when
    the child exits on its own (a crash) or the reloader is interrupted.
    """

    def __init__(
        self,
        startup_func: Callable[[], Awaitable[asyncio.subprocess.Process]],
        shutdown_func: Callable[[asyncio.subprocess.Process], Awaitable[None]],
        *,
        cwd: Path | None = None,
        reload_delay: float = 0.5,
        logger: logging.Logger | None = None,
    ) -> None:
        self.startup_func = startup_func
        self.shutdown_func = shutdown_func
        self.cwd = (cwd or Path.cwd()).resolve()
        self.logger = logger or get_logger("reloader")
        self.reload_delay = reload_delay
        self.process: asyncio.subprocess.Process | None = None
        self.should_exit = asyncio.Event()

        self._watcher = awatch(
            self.cwd,
            stop_event=self.should_exit,
            yield_on_timeout=True,
        )

    async def run(self) -> int:
        """Start the child, restarting it on changes, until it exits.

        Returns the last child exit code, or the code carried by a
        :class:`ReloaderError` raised by the startup function (e.g. ``124``
        for a startup timeout).
        """
        exit_code = 0
        try:
            await self._start()
            async for changes in self._watcher:
                current = self.process
                if current is not None and current.returncode is not None:
                    exit_code = current.returncode
                    break
                if changes:
                    self.logger.info(
                        _("Detected changes {paths}; restarting process.").format(
                            paths=", ".join(str(item[1]) for item in changes)
                        )
                    )
                    await self._restart()
        except ReloaderError as exc:
            exit_code = exc.exit_code
        finally:
            await self._stop()
        return exit_code

    async def _start(self) -> None:
        """Invoke the startup function and record the new child process."""
        self.process = await self.startup_func()
        self.logger.info(_("Started process [{}].").format(self.process.pid))

    async def _restart(self) -> None:
        """Stop the current child and start a fresh one after a short delay."""
        current = self.process
        if current is not None and current.returncode is None:
            await self.shutdown_func(current)
        await asyncio.sleep(self.reload_delay)
        await self._start()

    async def _stop(self) -> None:
        """Signal the watcher to stop and terminate any running child."""
        self.should_exit.set()
        current = self.process
        if current is not None and current.returncode is None:
            await self.shutdown_func(current)
