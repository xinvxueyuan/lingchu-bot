"""Tests for the signal forwarding helpers."""

from __future__ import annotations

import asyncio
import os
import signal
from typing import TYPE_CHECKING, cast

import pytest

from lingc_cli.handlers import signal as signal_mod
from lingc_cli.handlers.signal import terminate_process

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from types import FrameType

    from _pytest.monkeypatch import MonkeyPatch


class _FakeProcess:
    def __init__(self, *, returncode: int | None = None) -> None:
        self.returncode = returncode
        self.terminated = False
        self.pid = 1234
        self._waited = asyncio.Event()

    def terminate(self) -> None:
        self.terminated = True

    async def wait(self) -> None:
        self._waited.set()


async def test_terminate_process_windows_branch(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(signal_mod, "WINDOWS", True)
    proc = _FakeProcess()
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(
        signal_mod.os,
        "kill",
        lambda pid, sig: killed.append((pid, sig)),
    )
    await terminate_process(cast("asyncio.subprocess.Process", proc))
    assert killed == [(proc.pid, signal.CTRL_BREAK_EVENT)]
    assert proc.terminated is False
    assert proc._waited.is_set() is True


@pytest.mark.skipif(not hasattr(os, "getpgid"), reason="requires os.getpgid (POSIX)")
async def test_terminate_process_posix_branch_forwards_signal(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(signal_mod, "WINDOWS", False)
    proc = _FakeProcess()
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(signal_mod.os, "getpgid", lambda _pid: 9000)
    monkeypatch.setattr(
        signal_mod.os,
        "killpg",
        lambda pgid, sig: killed.append((pgid, sig)),
    )
    await terminate_process(
        cast("asyncio.subprocess.Process", proc), sig=signal.SIGTERM
    )
    assert killed == [(9000, signal.SIGTERM)]
    assert proc.terminated is False


async def test_terminate_process_is_noop_when_already_exited(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(signal_mod, "WINDOWS", True)
    proc = _FakeProcess(returncode=0)
    await terminate_process(cast("asyncio.subprocess.Process", proc))
    assert proc.terminated is False


async def test_terminate_process_windows_force_kill(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(signal_mod, "WINDOWS", True)
    proc = _FakeProcess()
    await terminate_process(
        cast("asyncio.subprocess.Process", proc), sig=signal_mod.SIGKILL
    )
    assert proc.terminated is True
    assert proc._waited.is_set() is True


async def test_terminate_process_force_kill_on_timeout(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(signal_mod, "WINDOWS", False)
    monkeypatch.setattr(signal_mod, "SIGKILL", 9)  # POSIX SIGKILL
    proc = _FakeProcess()
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(signal_mod.os, "getpgid", lambda _pid: 9000, raising=False)
    monkeypatch.setattr(
        signal_mod.os,
        "killpg",
        lambda pgid, sig: killed.append((pgid, sig)),
        raising=False,
    )

    async def fake_wait_for(awaitable: object, timeout: float | None) -> object:
        del timeout
        cast("Coroutine[object, object, object]", awaitable).close()
        raise TimeoutError

    monkeypatch.setattr(signal_mod.asyncio, "wait_for", fake_wait_for)
    await terminate_process(
        cast("asyncio.subprocess.Process", proc),
        sig=signal.SIGTERM,
        timeout=0.1,
    )
    assert killed == [(9000, signal.SIGTERM), (9000, 9)]


def test_shield_signals_context() -> None:
    assert signal_mod._shield_context.active() is False
    with signal_mod.shield_signals():
        assert signal_mod._shield_context.active() is True
    assert signal_mod._shield_context.active() is False


async def test_register_signal_forwarder_two_phase(
    monkeypatch: MonkeyPatch,
) -> None:
    proc = _FakeProcess()
    calls: list[tuple[int | None, float | None]] = []

    async def fake_terminate(
        process: object, *, sig: int | None, timeout: float | None = None
    ) -> None:
        del process
        calls.append((sig, timeout))

    monkeypatch.setattr(signal_mod, "terminate_process", fake_terminate)
    handlers: dict[int, object] = {}
    monkeypatch.setattr(signal_mod.signal, "getsignal", handlers.get)
    monkeypatch.setattr(signal_mod.signal, "signal", handlers.__setitem__)
    restore = signal_mod.register_signal_forwarder(
        cast("asyncio.subprocess.Process", proc), graceful_timeout=3.0
    )
    try:
        forward = cast(
            "Callable[[int, FrameType | None], None]", handlers[signal.SIGINT]
        )
        forward(signal.SIGINT, None)
        forward(signal.SIGINT, None)
        await asyncio.sleep(0)
    finally:
        restore()
    assert calls == [(signal.SIGINT, 3.0), (signal_mod.SIGKILL, None)]
