from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins import contracts


async def test_complete_subplugin_chat_forwards_explicit_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    complete_chat = AsyncMock(return_value="result")
    monkeypatch.setattr(contracts, "complete_chat", complete_chat)
    options = contracts.LLMOptions(
        provider="litellm",
        model="child-model",
        base_url=None,
        api_key=None,
        timeout=8.0,
    )
    messages = [{"role": "user", "content": "describe"}]

    assert (
        await contracts.complete_subplugin_chat(messages, options=options) == "result"
    )
    complete_chat.assert_awaited_once_with(messages, options=options)


def test_register_and_collect_subplugin_menu_features() -> None:
    """register_subplugin_menu_feature stores features; collect returns them."""
    from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins import (
        collect_subplugin_menu_features,
        register_subplugin_menu_feature,
        reset_subplugin_menu_features,
    )
    from src.plugins.nonebot_plugin_lingchu_bot.handle.menu import (
        LocalizedText,
        MenuAvailability,
        MenuFeature,
    )
    from src.plugins.nonebot_plugin_lingchu_bot.platforms import PlatformCapability

    original = collect_subplugin_menu_features()
    try:
        reset_subplugin_menu_features()
        feature = MenuFeature(
            "test-feature",
            "test_cmd",
            "entertainment",
            LocalizedText("测试", "Test"),
            LocalizedText("<arg>", "<arg>"),
            PlatformCapability.LLM_CHAT,
            (MenuAvailability("qq", "~onebot.v11"),),
        )
        register_subplugin_menu_feature(feature)
        collected = collect_subplugin_menu_features()
        assert feature in collected
        assert len(collected) == 1
    finally:
        reset_subplugin_menu_features()
        for feature in original:
            register_subplugin_menu_feature(feature)


def test_reset_subplugin_menu_features_clears_registry() -> None:
    """reset_subplugin_menu_features clears all registered features."""
    from src.plugins.nonebot_plugin_lingchu_bot.core.subplugins import (
        collect_subplugin_menu_features,
        register_subplugin_menu_feature,
        reset_subplugin_menu_features,
    )
    from src.plugins.nonebot_plugin_lingchu_bot.handle.menu import (
        LocalizedText,
        MenuAvailability,
        MenuFeature,
    )
    from src.plugins.nonebot_plugin_lingchu_bot.platforms import PlatformCapability

    original = collect_subplugin_menu_features()
    try:
        reset_subplugin_menu_features()
        feature = MenuFeature(
            "tmp-feature",
            "test_cmd",
            "entertainment",
            LocalizedText("临时", "Temp"),
            LocalizedText("", ""),
            PlatformCapability.LLM_CHAT,
            (MenuAvailability("qq", "~onebot.v11"),),
        )
        register_subplugin_menu_feature(feature)
        assert len(collect_subplugin_menu_features()) == 1
        reset_subplugin_menu_features()
        assert collect_subplugin_menu_features() == ()
    finally:
        reset_subplugin_menu_features()
        for feature in original:
            register_subplugin_menu_feature(feature)
