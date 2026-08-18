"""Tests for lingc_cli.handlers.env.env_snapshot."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from lingc_cli.handlers.env import env_snapshot

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


class _FakeDist:
    def __init__(self, name: str, version: str) -> None:
        self._name = name
        self.version = version
        self.metadata = {"Name": name}

    @property
    def name(self) -> str:
        return self._name


def _distributions() -> list[_FakeDist]:
    return [
        _FakeDist("nonebot", "2.3.3"),
        _FakeDist("nonebot-adapter-onebot", "2.4.3"),
        _FakeDist("nonebot-plugin-lingchu-bot", "1.0.0"),
        _FakeDist("typer", "0.12.0"),
    ]


def _patch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("importlib.metadata.distributions", _distributions)
    monkeypatch.setattr(
        "importlib.metadata.version",
        lambda name: "1.0.0" if name == "nonebot-plugin-lingchu-bot" else name,
    )
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(sys, "prefix", "/tmp/venv")
    monkeypatch.setattr(sys, "base_prefix", "/usr")


def test_env_snapshot_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch(monkeypatch)
    snapshot = env_snapshot(tmp_path)
    for key in (
        "os",
        "python_version",
        "python_path",
        "uv",
        "pip",
        "adapters",
        "lingchu_bot_version",
        "venv",
        "project_root",
    ):
        assert key in snapshot


def test_env_snapshot_tool_availability(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch(monkeypatch)
    snapshot = env_snapshot(tmp_path)
    assert snapshot["uv"] is True
    assert snapshot["pip"] is True


def test_env_snapshot_adapters_and_plugin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch(monkeypatch)
    snapshot = env_snapshot(tmp_path)
    adapters = snapshot["adapters"]
    assert [(item["name"], item["version"]) for item in adapters] == [
        ("nonebot-adapter-onebot", "2.4.3"),
    ]
    assert snapshot["lingchu_bot_version"] == "1.0.0"
    assert snapshot["venv"] == "active"
    assert snapshot["project_root"] == str(tmp_path)
