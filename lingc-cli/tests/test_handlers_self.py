"""Tests for lingc_cli.handlers.self.self_update."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lingc_cli.handlers import self as self_handler

if TYPE_CHECKING:
    import pytest


async def test_self_update_via_uv(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[tuple[str, ...]] = []

    async def _run(*command: str) -> None:
        commands.append(command)

    monkeypatch.setattr(self_handler, "_run", _run)
    monkeypatch.setattr(
        "shutil.which", lambda name: "/usr/bin/uv" if name == "uv" else None
    )
    method = await self_handler.self_update()
    assert method == "uv"
    assert commands == [("uv", "tool", "upgrade", "lingc-cli")]


async def test_self_update_via_pipx(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[tuple[str, ...]] = []

    async def _run(*command: str) -> None:
        commands.append(command)

    monkeypatch.setattr(self_handler, "_run", _run)
    monkeypatch.setattr(
        "shutil.which",
        lambda name: "/tmp/pipx" if name == "pipx" else None,
    )
    method = await self_handler.self_update()
    assert method == "pipx"
    assert commands == [("pipx", "upgrade", "lingc-cli")]


async def test_self_update_manual_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[tuple[str, ...]] = []

    async def _run(*command: str) -> None:
        commands.append(command)

    monkeypatch.setattr(self_handler, "_run", _run)
    monkeypatch.setattr("shutil.which", lambda _name: None)
    method = await self_handler.self_update()
    assert method == "manual"
    assert commands == []
