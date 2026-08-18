"""Signal forwarding for graceful child termination."""

from __future__ import annotations

import asyncio
import os
import signal
from typing import TYPE_CHECKING

from lingc_cli.consts import WINDOWS

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import FrameType
    from typing import Any

_FORWARD_SIGNALS = (signal.SIGINT, signal.SIGTERM)


async def terminate_process(
    process: asyncio.subprocess.Process,
    *,
    sig: int = signal.SIGINT,
) -> None:
    """Gracefully stop *process*, forwarding SIGINT/SIGTERM to it.

    No-op if the process already exited. On POSIX the signal is sent to the
    child's process group (created via ``start_new_session`` inside
    ``create_process``); on Windows ``process.terminate()`` is used. Either
    way the launcher waits for the child to exit before returning.
    """
    if process.returncode is not None:
        return

    if WINDOWS:
        process.terminate()
    else:
        try:
            os.killpg(os.getpgid(process.pid), sig)
        except (ProcessLookupError, PermissionError):
            process.terminate()

    await process.wait()


def register_signal_forwarder(
    process: asyncio.subprocess.Process,
) -> Callable[[], None]:
    """Install SIGINT/SIGTERM handlers that forward termination to *process*.

    Returns a callable that restores the previously installed handlers.
    """
    loop = asyncio.get_running_loop()
    previous: dict[
        int, Callable[[int, FrameType | None], Any] | signal.Handlers | None
    ] = {}
    tasks: set[asyncio.Task[None]] = set()

    def _forward(signum: int, frame: FrameType | None) -> None:
        del frame
        if process.returncode is not None:
            return
        sig = signal.SIGTERM if signum == signal.SIGTERM else signal.SIGINT
        task = loop.create_task(terminate_process(process, sig=sig))
        tasks.add(task)
        task.add_done_callback(tasks.discard)

    for sig in _FORWARD_SIGNALS:
        previous[sig] = signal.getsignal(sig)
        signal.signal(sig, _forward)

    def _restore() -> None:
        for sig, handler in previous.items():
            if handler is not None:
                signal.signal(sig, handler)

    return _restore
