from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.loader import (
    discover_subplugin_dirs,
    load_subplugins,
)

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_discover_subplugin_dirs_only_returns_public_packages(tmp_path: Path) -> None:
    child = tmp_path / "novelai_image"
    child.mkdir()
    (child / "__init__.py").write_text("", encoding="utf-8")
    private = tmp_path / "_private"
    private.mkdir()
    (private / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "not_a_package").mkdir()
    (tmp_path / "loader.py").write_text("", encoding="utf-8")

    assert discover_subplugin_dirs(tmp_path) == (child,)


def test_load_subplugins_loads_each_discovered_package(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tmp_path / "alpha"
    second = tmp_path / "beta"
    loaded = object()
    calls: list[Path] = []

    def fake_load_plugin(path: Path) -> Any:
        calls.append(path)
        return loaded if path == first else None

    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.loader.discover_subplugin_dirs",
        lambda: (first, second),
    )
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.loader.nonebot.load_plugin",
        fake_load_plugin,
    )

    assert load_subplugins() == {loaded}
    assert calls == [first, second]


def test_discovery_is_empty_without_child_packages(tmp_path: Path) -> None:
    assert discover_subplugin_dirs(tmp_path) == ()
