"""Safe startup and supervision for the ``lc run`` command."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys

from lingc_cli.consts import DEFAULT_STARTUP_TIMEOUT, STARTUP_MARKER
from lingc_cli.core import config, meta
from lingc_cli.exceptions import EnvironmentNotReadyError
from lingc_cli.handlers.process import await_process, create_process
from lingc_cli.handlers.reloader import Reloader, ReloaderError
from lingc_cli.handlers.signal import register_signal_forwarder, terminate_process
from lingc_cli.i18n import _


def _build_entry(python: str, cmd: list[str], cwd: Path) -> list[str]:
    """Compose the command list for the bot process.

    An explicit ``cmd`` wins; otherwise run ``bot.py`` when present, falling
    back to ``python -m nonebot``.
    """
    if cmd:
        return [python, *cmd]
    if (cwd / "bot.py").is_file():
        return [python, "bot.py"]
    return [python, "-m", "nonebot"]


async def _check_python(python: str) -> None:
    """Verify the resolved interpreter can be spawned, else raise.

    Raises :class:`EnvironmentNotReadyError` if the interpreter cannot be
    launched or its smoke probe returns a non-zero status.
    """
    try:
        proc = await create_process(
            [python, "--version"],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        raise EnvironmentNotReadyError(
            _("Failed to spawn Python interpreter: {python}").format(
                python=python,
            )
        ) from exc
    code = await await_process(proc)
    if code != 0:
        raise EnvironmentNotReadyError(
            _("Python interpreter exited with code {code}: {python}").format(
                code=code,
                python=python,
            )
        )


async def _forward_output(
    stream: asyncio.StreamReader | None,
    marker_found: asyncio.Event,
) -> None:
    """Stream child output to stdout, flagging the startup marker."""
    if stream is None:
        return
    async for raw in stream:
        text = raw.decode(errors="replace")
        if STARTUP_MARKER in text:
            marker_found.set()
        if sys.stdout is not None:
            sys.stdout.write(text)
            sys.stdout.flush()


async def _start_and_confirm(
    entry: list[str],
    cwd: Path,
    timeout: int,
) -> asyncio.subprocess.Process:
    """Spawn *entry*, forward output, and wait for a clean startup.

    Raises :class:`ReloaderError` with the exit code when the child exits
    before the startup marker (a crash) or when startup times out (``124``).
    """
    marker_found = asyncio.Event()
    proc = await create_process(
        entry,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    register_signal_forwarder(proc)
    reader_task = asyncio.create_task(_forward_output(proc.stdout, marker_found))
    exit_task = asyncio.create_task(proc.wait())
    marker_task = asyncio.create_task(marker_found.wait())
    done, _ = await asyncio.wait(
        {marker_task, exit_task},
        timeout=timeout,
        return_when=asyncio.FIRST_COMPLETED,
    )
    if exit_task in done:
        marker_task.cancel()
        await reader_task
        raise ReloaderError(await await_process(proc))
    if marker_task in done:
        await marker_task
        return proc
    marker_task.cancel()
    await terminate_process(proc)
    await reader_task
    raise ReloaderError(124)


async def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = DEFAULT_STARTUP_TIMEOUT,
    reload: bool = False,
) -> int:
    """Safely start the bot and supervise it until it exits.

    ``cmd`` may be empty to auto-select the entry point (``bot.py`` or
    ``-m nonebot``). Returns the child exit code, or ``124`` if startup
    timed out. With ``reload`` the child is restarted on file changes.
    """
    if cwd is None:
        cwd = config.get_cwd() or Path.cwd()
    cwd = cwd.resolve()
    python = meta.resolve_python(cwd)
    await _check_python(python)
    entry = _build_entry(python, cmd, cwd)

    if reload:
        reloader = Reloader(
            startup_func=lambda: _start_and_confirm(entry, cwd, timeout),
            shutdown_func=terminate_process,
            cwd=cwd,
        )
        return await reloader.run()

    try:
        proc = await _start_and_confirm(entry, cwd, timeout)
    except ReloaderError as exc:
        return exc.exit_code
    return await await_process(proc)
