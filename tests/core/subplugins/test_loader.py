from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.loader import (
    SUBPLUGIN_MODULES,
    load_subplugins,
)

if TYPE_CHECKING:
    import pytest


def test_declared_subplugins_are_explicit_and_stable() -> None:
    assert tuple(
        module.rsplit(".", maxsplit=1)[-1] for module in SUBPLUGIN_MODULES
    ) == (
        "llm_chat",
        "novelai_image",
    )


def test_load_subplugins_delegates_to_nonebot_plugin_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded = {object()}
    calls: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def fake_load_all_plugins(
        module_path: tuple[str, ...], plugin_dir: tuple[str, ...]
    ) -> Any:
        calls.append((module_path, plugin_dir))
        return loaded

    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.subplugins.loader.nonebot.load_all_plugins",
        fake_load_all_plugins,
    )

    assert load_subplugins() is loaded
    assert calls == [(SUBPLUGIN_MODULES, ())]
