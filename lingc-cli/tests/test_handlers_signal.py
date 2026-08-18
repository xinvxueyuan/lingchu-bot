"""Tests for the signal forwarding helpers."""

from __future__ import annotations

import asyncio
import os
import signal
from typing import TYPE_CHECKING

import pytest

from lingc_cli.handlers import signal as signal_mod
from lingc_cli.handlers.signal import terminate_process

if TYPE_CHECKING:
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
    await terminate_process(proc)
    assert proc.terminated is True
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
    await terminate_process(proc, sig=signal.SIGTERM)
    assert killed == [(9000, signal.SIGTERM)]
    assert proc.terminated is False


async def test_terminate_process_is_noop_when_already_exited(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(signal_mod, "WINDOWS", True)
    proc = _FakeProcess(returncode=0)
    await terminate_process(proc)
    assert proc.terminated is False
