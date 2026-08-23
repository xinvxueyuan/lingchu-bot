"""Tests for the low-level subprocess helpers."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, cast

from lingc_cli.handlers import process as process_mod
from lingc_cli.handlers.process import await_process, create_process

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


class _Proc:
    def __init__(self, code: int = 0) -> None:
        self._code = code
        self.waited = False

    async def wait(self) -> int:
        self.waited = True
        return self._code


async def test_create_process_delegates_to_create_subprocess_exec(
    monkeypatch: MonkeyPatch,
) -> None:
    captured: list[tuple] = []

    async def fake_exec(*args: str, **kwargs: object) -> _Proc:
        captured.append((args, kwargs))
        return _Proc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    proc = await create_process(
        ["python", "bot.py"],
        cwd=Path("proj"),
        env={"A": "1"},
        stdout=asyncio.subprocess.PIPE,
    )
    assert isinstance(proc, _Proc)
    args, kwargs = captured[0]
    assert args == ("python", "bot.py")
    assert kwargs["cwd"] == Path("proj")
    assert kwargs["env"] == {"A": "1"}
    assert kwargs["stdout"] == asyncio.subprocess.PIPE
    assert kwargs["stderr"] is None
    if process_mod.WINDOWS:
        assert kwargs["creationflags"] is not None
    else:
        assert kwargs["start_new_session"] is True


EXIT_CODE = 2


async def test_await_process_returns_exit_code() -> None:
    fake = cast("asyncio.subprocess.Process", _Proc(EXIT_CODE))
    assert await await_process(fake) == EXIT_CODE
