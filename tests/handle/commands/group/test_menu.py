from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle import menu
from src.plugins.nonebot_plugin_lingchu_bot.handle.menu import (
    LLBOT_IMPL,
    LLONEBOT_IMPL,
    MENU_FEATURES,
    MILKY_ADAPTER_ID,
    NAPCAT_IMPL,
    ONEBOT_V11_ADAPTER_ID,
    MenuRuntimeContext,
    menu_cmd,
    qq_menu_context,
    render_menu_for_context,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.group.command_triggers import (
    COMMAND_TRIGGERS,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.milky.v1_2.default import (
    menu as milky_menu_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.milky.v1_2.default.menu import (
    milkybot_menu,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.onebot.v11.default import (
    menu as onebot_menu_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.onebot.v11.default.menu import (
    onebot11_menu,
)
from src.plugins.nonebot_plugin_lingchu_bot.platforms import PlatformCapability
from tests.handle.commands.group.conftest import finish_text


def test_menu_registry_uses_known_command_keys() -> None:
    assert {feature.command_key for feature in MENU_FEATURES} <= set(COMMAND_TRIGGERS)


def test_extension_features_have_implementation_availability() -> None:
    extension_features = {
        feature.command_key: feature
        for feature in MENU_FEATURES
        if feature.command_key in {"send_announcement", "set_group_avatar"}
    }

    assert any(
        availability.implementation_name is not None
        for availability in extension_features["send_announcement"].availability
    )
    assert any(
        availability.implementation_name == NAPCAT_IMPL
        for availability in extension_features["set_group_avatar"].availability
        if availability.adapter_id == ONEBOT_V11_ADAPTER_ID
    )


def test_menu_registry_does_not_bypass_adapter_filtering() -> None:
    for feature in MENU_FEATURES:
        assert feature.availability
        assert all(item.adapter_id for item in feature.availability)


def test_onebot_unknown_hides_extension_features() -> None:
    rendered = render_menu_for_context(
        qq_menu_context(adapter_id=ONEBOT_V11_ADAPTER_ID),
        "zh_CN",
    )

    assert "发送群公告" not in rendered
    assert "设置群头像" not in rendered
    assert "设置群名称" in rendered
    assert "踢出群成员" in rendered


def test_onebot_llonebot_supports_announcement_only() -> None:
    rendered = render_menu_for_context(
        qq_menu_context(
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            implementation_name=LLONEBOT_IMPL,
            implementation_version="7.12.0",
            protocol_version="v11",
        ),
        "zh_CN",
    )

    assert "发送群公告" in rendered
    assert "设置群头像" not in rendered


def test_onebot_napcat_supports_announcement_and_avatar() -> None:
    rendered = render_menu_for_context(
        qq_menu_context(
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            implementation_name=NAPCAT_IMPL,
            implementation_version="4.18.0",
            protocol_version="v11",
        ),
        "zh_CN",
    )

    assert "发送群公告" in rendered
    assert "设置群头像" in rendered


def test_onebot_low_versions_hide_extension_features() -> None:
    llonebot_rendered = render_menu_for_context(
        qq_menu_context(
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            implementation_name=LLONEBOT_IMPL,
            implementation_version="7.11.9",
            protocol_version="v11",
        ),
        "zh_CN",
    )
    napcat_rendered = render_menu_for_context(
        qq_menu_context(
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            implementation_name=NAPCAT_IMPL,
            implementation_version="4.17.9",
            protocol_version="v11",
        ),
        "zh_CN",
    )

    assert "发送群公告" not in llonebot_rendered
    assert "发送群公告" not in napcat_rendered
    assert "设置群头像" not in napcat_rendered


def test_milky_llbot_supports_text_announcement_only() -> None:
    rendered = render_menu_for_context(
        qq_menu_context(adapter_id=MILKY_ADAPTER_ID, implementation_name=LLBOT_IMPL),
        "zh_CN",
    )

    assert "发送群公告: 发送群公告 <内容>" in rendered
    assert "发送群公告 <内容> [图片]" not in rendered


def test_milky_unknown_hides_announcement() -> None:
    rendered = render_menu_for_context(
        qq_menu_context(adapter_id=MILKY_ADAPTER_ID),
        "zh_CN",
    )

    assert "发送群公告" not in rendered
    assert "设置群头像" in rendered


def test_fail_closed_when_platform_capability_missing() -> None:
    context = MenuRuntimeContext(
        platform_id="qq",
        adapter_id=ONEBOT_V11_ADAPTER_ID,
        platform_capabilities=frozenset({PlatformCapability.GROUP_MANAGEMENT}),
    )

    rendered = render_menu_for_context(context, "zh_CN")

    assert "退出当前群" in rendered
    assert "禁言群成员" not in rendered


@pytest.mark.asyncio
async def test_menu_loader_imports_only_onebot11_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded_modules: list[str] = []
    called_handlers: list[str] = []

    def fake_import_module(module_path: str, _package: str | None = None) -> Any:
        loaded_modules.append(module_path)

        async def fake_import_handle_for_module() -> None:
            called_handlers.append(module_path)

        return SimpleNamespace(import_handle=fake_import_handle_for_module)

    monkeypatch.setattr(menu, "resolve_enabled_adapters", lambda: {"~onebot.v11"})
    monkeypatch.setattr(
        menu,
        "_ADAPTER_MODULES",
        {
            "~onebot.v11": (".qq.onebot.v11.default.menu",),
            "~milky": (".qq.milky.v1_2.default.menu",),
        },
    )
    monkeypatch.setattr(menu, "import_module", fake_import_module)
    menu._loaded_handlers.clear()

    await menu.import_handle()

    assert loaded_modules == [".qq.onebot.v11.default.menu"]
    assert called_handlers == [".qq.onebot.v11.default.menu"]


@pytest.mark.asyncio
async def test_menu_loader_imports_only_milky_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded_modules: list[str] = []

    async def fake_import_handle() -> None:
        return None

    def fake_import_module(module_path: str, _package: str | None = None) -> Any:
        loaded_modules.append(module_path)
        return SimpleNamespace(import_handle=fake_import_handle)

    monkeypatch.setattr(menu, "resolve_enabled_adapters", lambda: {"~milky"})
    monkeypatch.setattr(
        menu,
        "_ADAPTER_MODULES",
        {
            "~onebot.v11": (".qq.onebot.v11.default.menu",),
            "~milky": (".qq.milky.v1_2.default.menu",),
        },
    )
    monkeypatch.setattr(menu, "import_module", fake_import_module)
    menu._loaded_handlers.clear()

    await menu.import_handle()

    assert loaded_modules == [".qq.milky.v1_2.default.menu"]


@pytest.mark.asyncio
async def test_onebot11_menu_reads_version_info_and_finishes() -> None:
    bot = SimpleNamespace(
        get_version_info=AsyncMock(
            return_value={
                "protocol_version": "v11",
                "app_name": NAPCAT_IMPL,
                "app_version": "4.18.0",
            }
        )
    )

    with patch.object(menu_cmd, "finish") as mock_finish:
        await onebot11_menu(bot=bot)

    bot.get_version_info.assert_awaited_once()
    assert "设置群头像" in finish_text(mock_finish)
    assert "发送群公告" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_milky_menu_reads_impl_info_and_finishes() -> None:
    bot = SimpleNamespace(
        get_impl_info=AsyncMock(
            return_value=SimpleNamespace(impl_name=LLBOT_IMPL, impl_version="0.0.0")
        )
    )

    with patch.object(menu_cmd, "finish") as mock_finish:
        await milkybot_menu(bot=bot)

    bot.get_impl_info.assert_awaited_once()
    assert "发送群公告: 发送群公告 <内容>" in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_menu_fails_closed_when_detection_fails() -> None:
    bot = SimpleNamespace(get_version_info=AsyncMock(side_effect=RuntimeError("boom")))

    with (
        patch.object(onebot_menu_module.logger, "debug") as mock_debug,
        patch.object(menu_cmd, "finish") as mock_finish,
    ):
        await onebot11_menu(bot=bot)

    mock_debug.assert_called_once()
    assert "发送群公告" not in finish_text(mock_finish)
    assert "设置群头像" not in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_milky_menu_fails_closed_when_detection_fails() -> None:
    bot = SimpleNamespace(get_impl_info=AsyncMock(side_effect=RuntimeError("boom")))

    with (
        patch.object(milky_menu_module.logger, "debug") as mock_debug,
        patch.object(menu_cmd, "finish") as mock_finish,
    ):
        await milkybot_menu(bot=bot)

    mock_debug.assert_called_once()
    assert "发送群公告" not in finish_text(mock_finish)
