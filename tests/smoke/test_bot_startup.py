"""Smoke test verifying NoneBot and the Lingchu plugin load successfully."""

from __future__ import annotations

import nonebot


async def check_bot_startup() -> None:
    """Verify that NoneBot was initialized and the Lingchu plugin is loaded."""
    driver = nonebot.get_driver()
    assert driver is not None

    plugins = nonebot.get_loaded_plugins()
    plugin_names = {plugin.name for plugin in plugins}
    assert "nonebot_plugin_lingchu_bot" in plugin_names


async def test_bot_startup() -> None:
    """pytest entry point for ``check_bot_startup``."""
    await check_bot_startup()
