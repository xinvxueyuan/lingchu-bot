"""Tests for the safe-startup run handler."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from lingc_cli.exceptions import EnvironmentNotReadyError
from lingc_cli.handlers import run as run_mod
from lingc_cli.handlers.run import _build_entry, run

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

    from _pytest.monkeypatch import MonkeyPatch

TIMEOUT_EXIT = 124
CRASH_EXIT = 3
RUN_EXIT = 5
STARTUP_MARKER = run_mod.STARTUP_MARKER
MARKER_BYTES = STARTUP_MARKER.encode()
MINIMAL_PROJECT = "[tool.nonebot]\n"


def _write_project(tmp_path: Path, content: str = MINIMAL_PROJECT) -> None:
    (tmp_path / "pyproject.toml").write_text(content, encoding="utf-8")


class FakeProcess:
    """Minimal stand-in for asyncio.subprocess.Process."""

    def __init__(
        self,
        lines: list[bytes] = (),
        *,
        exit_code: int = 0,
        finished: bool = False,
        done: asyncio.Event | None = None,
    ) -> None:
        self._done = done or asyncio.Event()
        self._exit_code = exit_code
        self.returncode: int | None = None
        self.terminated = False
        self.wait_calls = 0
        self.stdin: object = None
        self.stderr: object = None
        self.stdout = self._stream(lines)
        if finished and done is None:
            self._finish(exit_code)

    async def _stream(self, lines: list[bytes]) -> AsyncIterator[bytes]:
        for line in lines:
            yield line
        await self._done.wait()

    async def wait(self) -> int:
        self.wait_calls += 1
        if self.returncode is None:
            await self._done.wait()
        return self._exit_code

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = 1
        self._done.set()

    def finish(self, code: int) -> None:
        self._finish(code)

    def _finish(self, code: int) -> None:
        self._exit_code = code
        self.returncode = code
        self._done.set()


def _fake_create(
    proc: FakeProcess | None = None,
    *,
    calls: list[list[str]] | None = None,
):
    async def create(
        cmd: list[str],
        *,
        cwd: Path | None = None,
        env: object = None,
        stdout: object = None,
        stderr: object = None,
    ) -> FakeProcess:
        del cwd, env, stdout, stderr
        if calls is not None:
            calls.append(cmd)
        if cmd[1] == "--version":
            return FakeProcess(exit_code=0, finished=True)
        return proc or FakeProcess()

    return create


def _patch_run(
    monkeypatch: MonkeyPatch,
    create: object,
    *,
    check_python: bool = False,
    forwarder: bool = False,
) -> None:
    """Patch run.create_process (and optional resolvers) with fakes."""
    monkeypatch.setattr(run_mod, "create_process", create)
    if check_python:

        async def noop_check(_python: str) -> None:
            return None

        monkeypatch.setattr(run_mod, "_check_python", noop_check)
    if forwarder:
        monkeypatch.setattr(
            run_mod, "register_signal_forwarder", lambda _proc: lambda: None
        )


def test_build_entry_uses_bot_py(tmp_path: Path) -> None:
    (tmp_path / "bot.py").write_text("x")
    entry = _build_entry("python", [], tmp_path)
    assert entry == ["python", "bot.py"]


def test_build_entry_generates_nb_cli_style_script(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        """
[tool.nonebot]
builtin_plugins = ["nonebot_plugin_docs"]

[tool.nonebot.adapters]
nonebot-adapter-onebot = [
    { name = "OneBot V11", module_name = "nonebot.adapters.onebot.v11" },
]
""",
    )

    entry = _build_entry("python", [], tmp_path)

    assert entry[:2] == ["python", "-c"]
    script = entry[2]
    assert "import importlib" in script
    assert "nonebot.init()" in script
    assert (
        "driver.register_adapter(importlib.import_module("
        '"nonebot.adapters.onebot.v11").Adapter)'
    ) in script
    assert 'nonebot.load_builtin_plugins("nonebot_plugin_docs")' in script
    assert 'nonebot.load_from_toml("pyproject.toml")' in script
    assert script.endswith("nonebot.run()\n")


def test_build_entry_supports_legacy_adapter_config(tmp_path: Path) -> None:
    _write_project(
        tmp_path,
        """
[tool.nonebot]
adapters = [
    { name = "OneBot V11", module_name = "nonebot.adapters.onebot.v11" },
]
""",
    )

    entry = _build_entry("python", [], tmp_path)

    assert '"nonebot.adapters.onebot.v11").Adapter)' in entry[2]


def test_build_entry_requires_nonebot_project(tmp_path: Path) -> None:
    with pytest.raises(EnvironmentNotReadyError, match=r"pyproject\.toml"):
        _build_entry("python", [], tmp_path)


def test_build_entry_rejects_invalid_adapter_config(tmp_path: Path) -> None:
    _write_project(tmp_path, '[tool.nonebot]\nadapters = "invalid"\n')

    with pytest.raises(EnvironmentNotReadyError, match="adapters"):
        _build_entry("python", [], tmp_path)


def test_build_entry_explicit_cmd_wins(tmp_path: Path) -> None:
    (tmp_path / "bot.py").write_text("x")
    entry = _build_entry("python", ["custom.py"], tmp_path)
    assert entry == ["python", "custom.py"]


async def test_run_reports_startup_timeout(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    proc = FakeProcess(lines=[], finished=False)
    _patch_run(monkeypatch, _fake_create(proc), check_python=True, forwarder=True)
    code = await run(cmd=[], cwd=tmp_path, timeout=0.1)
    assert code == TIMEOUT_EXIT
    assert proc.terminated is True


async def test_run_returns_nonzero_when_startup_crashes(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    proc = FakeProcess(
        lines=[b"[ERROR] boom"],
        exit_code=CRASH_EXIT,
        finished=True,
    )
    _patch_run(monkeypatch, _fake_create(proc), check_python=True, forwarder=True)
    code = await run(cmd=[], cwd=tmp_path, timeout=5)
    assert code == CRASH_EXIT


async def test_run_waits_for_marker_then_passes_exit_code(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    (tmp_path / "bot.py").write_text("x")
    proc = FakeProcess(lines=[MARKER_BYTES], exit_code=RUN_EXIT)
    calls: list[list[str]] = []
    _patch_run(
        monkeypatch,
        _fake_create(proc, calls=calls),
        check_python=True,
        forwarder=True,
    )

    run_task = asyncio.create_task(run(cmd=[], cwd=tmp_path, timeout=5))
    await asyncio.sleep(0.02)
    proc.finish(RUN_EXIT)
    code = await asyncio.wait_for(run_task, 10)
    assert code == RUN_EXIT
    assert proc.terminated is False
    assert calls[0] == ["python", "bot.py"]


async def test_check_python_raises_when_spawn_fails(
    monkeypatch: MonkeyPatch,
) -> None:
    async def boom(
        cmd: list[str],
        *,
        cwd: Path | None = None,
        env: object = None,
        stdout: object = None,
        stderr: object = None,
    ) -> FakeProcess:
        del cwd, env, stdout, stderr
        raise FileNotFoundError(cmd[0])

    _patch_run(monkeypatch, boom)
    with pytest.raises(EnvironmentNotReadyError):
        await run_mod._check_python("no-such-python")
