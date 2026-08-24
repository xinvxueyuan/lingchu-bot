"""Signal forwarding for graceful child termination."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
import os
import signal
from typing import TYPE_CHECKING

from lingc_cli.consts import WINDOWS

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from types import FrameType

_FORWARD_SIGNALS = (
    (signal.SIGINT, signal.SIGTERM, signal.SIGBREAK)
    if WINDOWS
    else (signal.SIGINT, signal.SIGTERM)
)

# Windows lacks SIGKILL; None is the force-kill sentinel (maps to terminate()).
SIGKILL: int | None = getattr(signal, "SIGKILL", None)

DEFAULT_GRACEFUL_TIMEOUT = 10.0


class _ShieldContext:
    """Reference-counted guard that suppresses reentrant signals."""

    def __init__(self) -> None:
        self._counter = 0

    def acquire(self) -> None:
        self._counter += 1

    def release(self) -> None:
        self._counter -= 1

    def active(self) -> bool:
        return self._counter > 0


_shield_context = _ShieldContext()


@contextmanager
def shield_signals() -> Generator[None]:
    """Suppress reentrant signal forwarding while terminating a child.

    Signals received while the context is active are ignored by the
    forwarder, preventing a second signal from interrupting an ongoing
    graceful shutdown.
    """
    _shield_context.acquire()
    try:
        yield
    finally:
        _shield_context.release()


def _send_signal(process: asyncio.subprocess.Process, sig: int | None) -> None:
    """Deliver *sig* to *process*, falling back to ``terminate()``.

    On Windows a graceful signal is delivered via ``CTRL_BREAK_EVENT``
    and ``SIGKILL`` maps to ``terminate()``; on POSIX the signal is sent
    to the child's process group.
    """
    if WINDOWS:
        if sig == SIGKILL:
            process.terminate()
        else:
            os.kill(process.pid, signal.CTRL_BREAK_EVENT)
    else:
        assert sig is not None  # POSIX 始终有 SIGKILL
        try:
            os.killpg(os.getpgid(process.pid), sig)
        except (ProcessLookupError, PermissionError):
            process.terminate()


async def terminate_process(
    process: asyncio.subprocess.Process,
    *,
    sig: int | None = signal.SIGINT,
    timeout: float | None = None,
) -> None:
    """Gracefully stop *process*, forwarding *sig* to it.

    No-op if the process already exited. On Windows the graceful signal
    is delivered via ``CTRL_BREAK_EVENT``; on POSIX it is sent to the
    child's process group (created via ``start_new_session`` inside
    ``create_process``). If the child does not exit within *timeout*
    seconds, it is forcibly destroyed (``SIGKILL`` on POSIX,
    ``terminate()`` on Windows). lingc-cli waits for the child to exit
    before returning.
    """
    if process.returncode is not None:
        return

    with shield_signals():
        _send_signal(process, sig)
        try:
            await asyncio.wait_for(process.wait(), timeout)
        except TimeoutError:
            _send_signal(process, SIGKILL)
            await process.wait()


def register_signal_forwarder(
    process: asyncio.subprocess.Process,
    *,
    graceful_timeout: float = DEFAULT_GRACEFUL_TIMEOUT,
) -> Callable[[], None]:
    """Install signal handlers that forward termination to *process*.

    Handles SIGINT/SIGTERM (plus SIGBREAK on Windows). The first signal
    triggers a graceful shutdown within *graceful_timeout* seconds; any
    further signal forces an immediate kill. Returns a callable that
    restores the previously installed handlers.
    """
    loop = asyncio.get_running_loop()
    previous: dict[
        int,
        Callable[[int, FrameType | None], object] | signal.Handlers | int | None,
    ] = {}
    tasks: set[asyncio.Task[None]] = set()
    signals_seen = 0

    def _forward(signum: int, frame: FrameType | None) -> None:
        nonlocal signals_seen
        del frame
        if process.returncode is not None or _shield_context.active():
            return
        signals_seen += 1
        if signals_seen == 1:
            sig = signal.SIGTERM if signum == signal.SIGTERM else signal.SIGINT
            task = loop.create_task(
                terminate_process(process, sig=sig, timeout=graceful_timeout)
            )
        else:
            task = loop.create_task(terminate_process(process, sig=SIGKILL))
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


__all__ = [
    "DEFAULT_GRACEFUL_TIMEOUT",
    "register_signal_forwarder",
    "shield_signals",
    "terminate_process",
]
