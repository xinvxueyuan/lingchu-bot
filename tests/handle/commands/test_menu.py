from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle import menu
from src.plugins.nonebot_plugin_lingchu_bot.handle.menu import (
    _DEFAULT_MENU_FEATURES,
    MENU_FEATURES,
    NAPCAT_IMPL,
    ONEBOT_V11_ADAPTER_ID,
    LocalizedText,
    MenuPage,
    MenuRuntimeContext,
    menu_cmd,
    menu_page_cmds,
    qq_menu_context,
    render_menu_for_context,
    render_menu_index,
    render_menu_page,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    menu as onebot_menu_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    onebot11_menu,
    onebot11_menu_pages,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.triggers import (
    COMMAND_TRIGGERS,
)
from src.plugins.nonebot_plugin_lingchu_bot.platforms import PlatformCapability
from tests.handle.commands.conftest import finish_text


def test_menu_registry_uses_known_command_keys() -> None:
    assert {feature.command_key for feature in MENU_FEATURES} <= set(COMMAND_TRIGGERS)
    assert {feature.command_key for feature in _DEFAULT_MENU_FEATURES} <= set(
        COMMAND_TRIGGERS
    )
    assert {feature.command_key for feature in MENU_FEATURES} == {
        feature.command_key for feature in _DEFAULT_MENU_FEATURES
    }


def test_set_menu_pages_replaces_runtime_lookup() -> None:
    custom_pages = (
        MenuPage(
            "member-management",
            LocalizedText("成员", "Members"),
            command=LocalizedText("成员管理", "member-management"),
        ),
    )

    try:
        menu.set_menu_pages(custom_pages)
        rendered = render_menu_page(
            "member-management",
            qq_menu_context(adapter_id=ONEBOT_V11_ADAPTER_ID),
            "zh_CN",
        )
        assert rendered.startswith("成员")
    finally:
        menu.set_menu_pages(menu._DEFAULT_MENU_PAGES)


def test_set_menu_features_replaces_runtime_data() -> None:
    default_feature = menu._DEFAULT_MENU_FEATURES[0]
    custom_feature = default_feature.__class__(
        default_feature.id,
        default_feature.command_key,
        default_feature.section_id,
        LocalizedText("自定义摘要", "Custom summary"),
        default_feature.usage,
        default_feature.platform_capability,
        default_feature.availability,
    )

    try:
        menu.set_menu_features((custom_feature,))
        rendered = render_menu_page(
            "member-management",
            qq_menu_context(adapter_id=ONEBOT_V11_ADAPTER_ID),
            "zh_CN",
        )
        assert "自定义摘要" in rendered
    finally:
        menu.set_menu_features(menu._DEFAULT_MENU_FEATURES)


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


def test_menu_index_lists_direct_submenus_only() -> None:
    rendered = render_menu_index(
        qq_menu_context(adapter_id=ONEBOT_V11_ADAPTER_ID),
        "zh_CN",
    )

    assert "灵初功能菜单" in rendered
    assert "- 成员管理" in rendered
    assert "- 发言管理" in rendered
    assert "- 群聊管理" in rendered
    assert "- 远程管理" in rendered
    assert "- 成员管理: 成员管理" not in rendered
    assert "踢出群成员" not in rendered
    assert "禁言群成员" not in rendered
    assert "设置群名称" not in rendered
    assert "远程禁言" not in rendered


def test_menu_index_keeps_distinct_english_title_and_trigger() -> None:
    rendered = render_menu_index(
        qq_menu_context(adapter_id=ONEBOT_V11_ADAPTER_ID),
        "en_US",
    )

    assert "Lingchu Menu" in rendered
    assert "- Member Management: member-management" in rendered
    assert "- Speech Management: speech-management" in rendered
    assert "- Group Chat Management: group-chat-management" in rendered
    assert "- Remote Management: remote-management" in rendered


def test_menu_page_commands_do_not_claim_announcement_alias() -> None:
    assert set(menu_page_cmds) == {
        "member-management",
        "speech-management",
        "group-chat-management",
        "remote-management",
        "system-management",
    }
    assert COMMAND_TRIGGERS["send_announcement"].chinese_aliases == {
        "发群公告",
        "群公告",
    }


def test_render_menu_for_context_keeps_index_compatibility() -> None:
    assert render_menu_for_context(
        qq_menu_context(adapter_id=ONEBOT_V11_ADAPTER_ID),
        "zh_CN",
    ) == render_menu_index(
        qq_menu_context(adapter_id=ONEBOT_V11_ADAPTER_ID),
        "zh_CN",
    )


def test_member_management_page_lists_member_commands_only() -> None:
    rendered = render_menu_page(
        "member-management",
        qq_menu_context(adapter_id=ONEBOT_V11_ADAPTER_ID),
        "zh_CN",
    )

    assert "成员管理" in rendered
    assert "踢出群成员" in rendered
    assert "拉黑群成员" in rendered
    assert "清空本群黑名单" in rendered
    assert "拉白群成员" in rendered
    assert "删除本群白名单" in rendered
    assert "设置群名片" in rendered
    assert "禁言群成员" not in rendered
    assert "设置群名称" not in rendered


def test_member_management_page_hides_denied_commands() -> None:
    rendered = render_menu_page(
        "member-management",
        qq_menu_context(adapter_id=ONEBOT_V11_ADAPTER_ID),
        "zh_CN",
        allowed_command_keys=frozenset({"set_member_card"}),
    )

    assert "踢出群成员" not in rendered
    assert "设置群名片 (只读)" not in rendered
    assert "设置群名片" in rendered


def test_speech_management_page_lists_speech_commands_only() -> None:
    rendered = render_menu_page(
        "speech-management",
        qq_menu_context(adapter_id=ONEBOT_V11_ADAPTER_ID),
        "zh_CN",
    )

    assert "发言管理" in rendered
    assert "禁言群成员" in rendered
    assert "撤回群消息" in rendered
    assert "关闭全体禁言" in rendered
    assert "踢出群成员" not in rendered
    assert "退出当前群" not in rendered


def test_onebot_unknown_hides_extension_features() -> None:
    rendered = render_menu_page(
        "group-chat-management",
        qq_menu_context(adapter_id=ONEBOT_V11_ADAPTER_ID),
        "zh_CN",
    )

    assert "发送群公告" not in rendered
    assert "设置群头像" not in rendered
    assert "设置群名称" in rendered
    assert "退出当前群" in rendered
    assert "踢出群成员" not in rendered


def test_onebot_llonebot_hides_extension_features() -> None:
    rendered = render_menu_page(
        "group-chat-management",
        qq_menu_context(
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            implementation_name="LLOneBot",
            implementation_version="7.12.0",
            protocol_version="v11",
        ),
        "zh_CN",
    )

    assert "发送群公告" not in rendered
    assert "设置群头像" not in rendered


def test_onebot_napcat_supports_announcement_and_avatar() -> None:
    rendered = render_menu_page(
        "group-chat-management",
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
    napcat_rendered = render_menu_page(
        "group-chat-management",
        qq_menu_context(
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            implementation_name=NAPCAT_IMPL,
            implementation_version="4.17.9",
            protocol_version="v11",
        ),
        "zh_CN",
    )

    assert "发送群公告" not in napcat_rendered
    assert "设置群头像" not in napcat_rendered


def test_fail_closed_when_platform_capability_missing() -> None:
    context = MenuRuntimeContext(
        platform_id="qq",
        adapter_id=ONEBOT_V11_ADAPTER_ID,
        platform_capabilities=frozenset({PlatformCapability.GROUP_MANAGEMENT}),
    )

    rendered = render_menu_page("group-chat-management", context, "zh_CN")

    assert "退出当前群" in rendered
    assert "禁言群成员" not in rendered


def test_remote_management_page_lists_remote_commands() -> None:
    rendered = render_menu_page(
        "remote-management",
        qq_menu_context(adapter_id=ONEBOT_V11_ADAPTER_ID),
        "zh_CN",
    )

    assert "远程管理" in rendered
    assert "远程禁言" in rendered
    assert "远程解禁" in rendered
    assert "远程全体禁言" in rendered
    assert "远程全体解禁" in rendered
    assert "远程踢出" in rendered
    assert "远程拉黑" in rendered
    assert "远程删黑" in rendered
    assert "踢出群成员" not in rendered
    assert "禁言群成员" not in rendered


def test_remote_management_page_hides_announcement_for_unsupported_impl() -> None:
    rendered = render_menu_page(
        "remote-management",
        qq_menu_context(adapter_id=ONEBOT_V11_ADAPTER_ID),
        "zh_CN",
    )

    assert "远程禁言" in rendered
    assert "远程公告" not in rendered


def test_remote_management_page_shows_announcement_for_napcat() -> None:
    rendered = render_menu_page(
        "remote-management",
        qq_menu_context(
            adapter_id=ONEBOT_V11_ADAPTER_ID,
            implementation_name=NAPCAT_IMPL,
            implementation_version="4.18.0",
            protocol_version="v11",
        ),
        "zh_CN",
    )

    assert "远程公告" in rendered
    assert "远程禁言" in rendered


@pytest.mark.asyncio
async def test_menu_loader_imports_only_onebot11_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called_handlers: list[str] = []
    load_calls: list[str] = []

    async def fake_handler() -> None:
        called_handlers.append(".qq.adapters.onebot11.default.menu")

    def fake_load_adapter_handlers(
        adapter_id: str,
        _adapter_modules: dict[str, tuple[str, ...]],
        _package: str,
    ) -> tuple[Any, ...]:
        load_calls.append(adapter_id)
        return (fake_handler,)

    monkeypatch.setattr(menu, "resolve_enabled_adapters", lambda: {"~onebot.v11"})
    monkeypatch.setattr(menu, "load_adapter_handlers", fake_load_adapter_handlers)

    await menu.import_handle()

    assert load_calls == ["~onebot.v11"]
    assert called_handlers == [".qq.adapters.onebot11.default.menu"]


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
    assert "群聊管理" in finish_text(mock_finish)
    assert "设置群头像" not in finish_text(mock_finish)
    assert "发送群公告" not in finish_text(mock_finish)


@pytest.mark.asyncio
async def test_onebot11_menu_page_reads_version_info_and_finishes() -> None:
    bot = SimpleNamespace(
        get_version_info=AsyncMock(
            return_value={
                "protocol_version": "v11",
                "app_name": NAPCAT_IMPL,
                "app_version": "4.18.0",
            }
        )
    )
    command = menu_page_cmds["group-chat-management"]

    with patch.object(command, "finish") as mock_finish:
        await onebot11_menu_pages["group-chat-management"](bot=bot)

    bot.get_version_info.assert_awaited_once()
    assert "设置群头像" in finish_text(mock_finish)
    assert "发送群公告" in finish_text(mock_finish)


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
