"""Tests for the file-watch reloader."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from watchfiles import Change

from lingc_cli.handlers.reloader import Reloader

if TYPE_CHECKING:
    import asyncio
    from collections.abc import AsyncGenerator, Sequence


class _Proc:
    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.returncode: int | None = None
        self.terminated = False

    def terminate(self) -> None:
        self.terminated = True


async def _fake_watcher(
    steps: Sequence[set[tuple[Change, str]]],
) -> AsyncGenerator[set[tuple[Change, str]]]:
    for step in steps:
        yield step


async def test_reloader_restarts_on_change() -> None:
    procs = [_Proc(1), _Proc(2)]
    started: list[_Proc] = []

    async def startup() -> asyncio.subprocess.Process:
        proc = procs[len(started)]
        started.append(proc)
        return cast("asyncio.subprocess.Process", proc)

    async def shutdown(proc: asyncio.subprocess.Process) -> None:
        proc.terminate()

    reloader = Reloader(
        startup,
        shutdown,
        cwd=Path("proj"),
        reload_delay=0,
    )
    reloader._watcher = _fake_watcher([{(Change.added, str(Path("proj") / "a.py"))}])
    code = await reloader.run()
    assert code == 0
    assert [p.pid for p in started] == [1, 2]
    assert procs[0].terminated is True
    assert procs[1].terminated is True


async def test_reloader_returns_child_exit_code_when_it_crashes() -> None:
    procs = [_Proc(1)]
    started: list[_Proc] = []

    async def startup() -> asyncio.subprocess.Process:
        proc = procs[len(started)]
        started.append(proc)
        return cast("asyncio.subprocess.Process", proc)

    async def shutdown(proc: asyncio.subprocess.Process) -> None:
        proc.terminate()

    reloader = Reloader(
        startup,
        shutdown,
        cwd=Path("proj"),
        reload_delay=0,
    )
    crash_code = 2
    procs[0].returncode = crash_code
    reloader._watcher = _fake_watcher([set()])
    code = await reloader.run()
    assert code == crash_code
