from collections import Counter
from typing import TypedDict

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands import triggers
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.triggers import (
    COMMAND_TRIGGERS,
)


class ExpectedTrigger(TypedDict):
    primary: str
    english: str
    chinese_aliases: set[str]
    english_aliases: set[str]


EXPECTED_TRIGGERS: dict[str, ExpectedTrigger] = {
    "menu": {
        "primary": "菜单",
        "english": "menu",
        "chinese_aliases": {"帮助", "功能", "功能列表", "指令", "命令列表"},
        "english_aliases": {"help", "commands"},
    },
    "member_mute": {
        "primary": "禁言",
        "english": "mute",
        "chinese_aliases": {"禁言用户", "禁言群成员", "禁言成员", "禁", "封禁"},
        "english_aliases": {"ban", "mute-member", "ban-member"},
    },
    "manage_handle_defaults": {
        "primary": "设置功能默认值",
        "english": "set-handle-default",
        "chinese_aliases": {"功能默认值", "查看功能默认值"},
        "english_aliases": {"handle-defaults", "list-handle-defaults"},
    },
    "set_default_mute_duration": {
        "primary": "设置默认禁言",
        "english": "set-default-mute",
        "chinese_aliases": {"默认禁言时长", "设置默认禁言时长"},
        "english_aliases": {"default-mute-duration"},
    },
    "member_unmute": {
        "primary": "解禁",
        "english": "unmute",
        "chinese_aliases": {
            "解禁用户",
            "解禁群成员",
            "解禁成员",
            "解禁",
            "解封",
            "解除封禁",
            "解除禁言",
        },
        "english_aliases": {"pardon", "unmute-member"},
    },
    "whole_mute": {
        "primary": "全员禁言",
        "english": "mute-all",
        "chinese_aliases": {
            "开启全体禁言",
            "全禁",
            "全禁言",
            "全体禁言",
            "全体禁言开启",
            "全员禁言开启",
            "开启全员禁言",
            "禁言群",
        },
        "english_aliases": {"mute-group", "enable-whole-mute"},
    },
    "whole_unmute": {
        "primary": "全体解禁",
        "english": "unmute-all",
        "chinese_aliases": {
            "全员解禁",
            "关闭全体禁言",
            "解除全体禁言",
            "解禁全体",
            "解禁全员",
            "全解",
            "全解禁",
            "全体解禁",
            "关闭全员禁言",
            "解除全员禁言",
            "解禁群",
        },
        "english_aliases": {"unmute-group", "disable-whole-mute"},
    },
    "recall_message": {
        "primary": "撤回",
        "english": "recall",
        "chinese_aliases": {"撤回消息", "批量撤回"},
        "english_aliases": {"delete-message", "recall-message"},
    },
    "set_group_name": {
        "primary": "设置群名称",
        "english": "set-group-name",
        "chinese_aliases": {"改群名", "修改群名称", "设置群名"},
        "english_aliases": {"rename-group"},
    },
    "set_group_avatar": {
        "primary": "设置群头像",
        "english": "set-group-avatar",
        "chinese_aliases": {"改群头像", "修改群头像"},
        "english_aliases": {"change-group-avatar"},
    },
    "set_member_card": {
        "primary": "设置群名片",
        "english": "set-member-card",
        "chinese_aliases": {"改群名片", "修改群名片", "设置成员名片"},
        "english_aliases": {"set-group-card"},
    },
    "set_member_title": {
        "primary": "设置群头衔",
        "english": "set-member-title",
        "chinese_aliases": {"设置专属头衔", "设置群成员专属头衔", "改群头衔"},
        "english_aliases": {"set-special-title"},
    },
    "set_member_admin": {
        "primary": "设置群管理员",
        "english": "set-member-admin",
        "chinese_aliases": {"设置管理员", "任命群管理员"},
        "english_aliases": {"set-admin", "promote-admin"},
    },
    "unset_member_admin": {
        "primary": "取消群管理员",
        "english": "unset-member-admin",
        "chinese_aliases": {"取消管理员", "撤销群管理员"},
        "english_aliases": {"unset-admin", "revoke-admin"},
    },
    "kick_member": {
        "primary": "踢出",
        "english": "kick-member",
        "chinese_aliases": {"踢", "踢出群成员", "踢人", "移出群成员"},
        "english_aliases": {"kick", "remove-member"},
    },
    "block_member": {
        "primary": "拉黑",
        "english": "block",
        "chinese_aliases": {"拉黑用户"},
        "english_aliases": {"block-member"},
    },
    "global_block_member": {
        "primary": "全局拉黑",
        "english": "global-block",
        "chinese_aliases": {"全局拉黑用户"},
        "english_aliases": {"global-block-member"},
    },
    "unblock_member": {
        "primary": "删黑",
        "english": "unblock",
        "chinese_aliases": {"删除黑名单"},
        "english_aliases": {"unblock-member"},
    },
    "global_unblock_member": {
        "primary": "全局删黑",
        "english": "global-unblock",
        "chinese_aliases": {"全局删除黑名单"},
        "english_aliases": {"global-unblock-member"},
    },
    "clear_blocklist": {
        "primary": "清空黑名单",
        "english": "clear-blocklist",
        "chinese_aliases": set(),
        "english_aliases": set(),
    },
    "global_clear_blocklist": {
        "primary": "全局清空黑名单",
        "english": "global-clear-blocklist",
        "chinese_aliases": set(),
        "english_aliases": set(),
    },
    "protect_member": {
        "primary": "拉白",
        "english": "protect",
        "chinese_aliases": {"拉白用户"},
        "english_aliases": {"protect-member"},
    },
    "global_protect_member": {
        "primary": "全局拉白",
        "english": "global-protect",
        "chinese_aliases": {"全局拉白用户"},
        "english_aliases": {"global-protect-member"},
    },
    "unprotect_member": {
        "primary": "删白",
        "english": "unprotect",
        "chinese_aliases": {"删除白名单"},
        "english_aliases": {"unprotect-member"},
    },
    "global_unprotect_member": {
        "primary": "全局删白",
        "english": "global-unprotect",
        "chinese_aliases": {"全局删除白名单"},
        "english_aliases": {"global-unprotect-member"},
    },
    "send_announcement": {
        "primary": "发送群公告",
        "english": "send-announcement",
        "chinese_aliases": {"发群公告", "群公告"},
        "english_aliases": {"announce", "group-announcement"},
    },
    "leave_group": {
        "primary": "退出群",
        "english": "leave-group",
        "chinese_aliases": {"退群", "退出当前群"},
        "english_aliases": {"quit-group"},
    },
    "remote_mute": {
        "primary": "远程禁言",
        "english": "remote-mute",
        "chinese_aliases": {"跨群禁言", "远程禁言用户", "远程禁言成员"},
        "english_aliases": {"remote-ban", "cross-group-mute"},
    },
    "remote_unmute": {
        "primary": "远程解禁",
        "english": "remote-unmute",
        "chinese_aliases": {"跨群解禁", "远程解禁用户", "远程解禁成员"},
        "english_aliases": {"remote-pardon", "cross-group-unmute"},
    },
    "remote_whole_mute": {
        "primary": "远程全体禁言",
        "english": "remote-mute-all",
        "chinese_aliases": {"跨群全体禁言", "远程全员禁言", "远程开启全体禁言"},
        "english_aliases": {"remote-mute-group", "cross-group-mute-all"},
    },
    "remote_whole_unmute": {
        "primary": "远程全体解禁",
        "english": "remote-unmute-all",
        "chinese_aliases": {"跨群全体解禁", "远程全员解禁", "远程关闭全体禁言"},
        "english_aliases": {"remote-unmute-group", "cross-group-unmute-all"},
    },
    "remote_kick": {
        "primary": "远程踢出",
        "english": "remote-kick",
        "chinese_aliases": {"跨群踢出", "远程踢人", "远程移出群成员"},
        "english_aliases": {"remote-kick-member", "cross-group-kick"},
    },
    "remote_block": {
        "primary": "远程拉黑",
        "english": "remote-block",
        "chinese_aliases": {"跨群拉黑", "远程拉黑用户"},
        "english_aliases": {"remote-block-member", "cross-group-block"},
    },
    "remote_unblock": {
        "primary": "远程删黑",
        "english": "remote-unblock",
        "chinese_aliases": {"跨群删黑", "远程删除黑名单"},
        "english_aliases": {"remote-unblock-member", "cross-group-unblock"},
    },
    "remote_announcement": {
        "primary": "远程公告",
        "english": "remote-announcement",
        "chinese_aliases": {"跨群公告", "远程群公告", "远程发公告"},
        "english_aliases": {"remote-notice", "cross-group-announcement"},
    },
    "mass_announcement": {
        "primary": "群发公告",
        "english": "mass-announcement",
        "chinese_aliases": {"批量公告", "多群公告"},
        "english_aliases": {"broadcast-announcement", "multi-group-announcement"},
    },
    "restart_protocol_endpoint": {
        "primary": "重启协议端",
        "english": "restart-protocol-endpoint",
        "chinese_aliases": {"重启协议", "重启应用端"},
        "english_aliases": {"restart-protocol", "restart-endpoint"},
    },
    "bot_silence": {
        "primary": "闭嘴",
        "english": "silence",
        "chinese_aliases": set(),
        "english_aliases": set(),
    },
    "bot_speak": {
        "primary": "说话",
        "english": "speak",
        "chinese_aliases": set(),
        "english_aliases": set(),
    },
    "bot_boot": {
        "primary": "开机",
        "english": "boot",
        "chinese_aliases": set(),
        "english_aliases": set(),
    },
    "bot_shutdown": {
        "primary": "关机",
        "english": "shutdown",
        "chinese_aliases": set(),
        "english_aliases": set(),
    },
    "chat": {
        "primary": "聊天",
        "english": "chat",
        "chinese_aliases": set(),
        "english_aliases": set(),
    },
    "novelai_image": {
        "primary": "生图",
        "english": "novelai-image",
        "chinese_aliases": {"生成图片", "画图"},
        "english_aliases": {"novelai", "generate-image"},
    },
}


def test_command_trigger_catalog_keeps_chinese_triggers() -> None:
    assert set(COMMAND_TRIGGERS) == set(EXPECTED_TRIGGERS)

    for command_key, expected in EXPECTED_TRIGGERS.items():
        trigger = COMMAND_TRIGGERS[command_key]

        assert trigger.chinese == expected["primary"]
        assert trigger.chinese_aliases == expected["chinese_aliases"]
        assert trigger.primary_for("zh_CN") == expected["primary"]
        assert trigger.aliases_for("zh_CN") == expected["chinese_aliases"]
        assert expected["english"] not in trigger.aliases_for("zh_CN")
        assert trigger.english_aliases.isdisjoint(trigger.aliases_for("zh_CN"))


def test_command_trigger_catalog_registers_english_triggers_by_locale() -> None:
    for command_key, expected in EXPECTED_TRIGGERS.items():
        trigger = COMMAND_TRIGGERS[command_key]

        assert trigger.english == expected["english"]
        assert trigger.english_aliases == expected["english_aliases"]
        assert trigger.primary_for("en_US") == expected["english"]
        assert trigger.aliases_for("en_US") == expected["english_aliases"]
        assert expected["primary"] not in trigger.aliases_for("en_US")
        assert trigger.chinese_aliases.isdisjoint(trigger.aliases_for("en_US"))


def test_command_trigger_catalog_uses_configured_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trigger = COMMAND_TRIGGERS["member_mute"]

    monkeypatch.setattr(triggers, "get_configured_locale", lambda: "zh_CN")
    assert trigger.primary == "禁言"
    assert trigger.aliases == {"禁言用户", "禁言群成员", "禁言成员", "禁", "封禁"}

    monkeypatch.setattr(triggers, "get_configured_locale", lambda: "en_US")
    assert trigger.primary == "mute"
    assert trigger.aliases == {"ban", "mute-member", "ban-member"}


def test_command_trigger_catalog_has_no_cross_command_duplicates() -> None:
    all_triggers = [
        value
        for trigger in COMMAND_TRIGGERS.values()
        for value in {
            trigger.chinese,
            trigger.english,
            *trigger.chinese_aliases,
            *trigger.english_aliases,
        }
    ]

    duplicates = {value for value, count in Counter(all_triggers).items() if count > 1}

    assert duplicates == set()
