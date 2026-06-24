import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.triggers import (
    CommandTrigger,
    CommandTriggerOverride,
    build_command_triggers,
)


def test_command_trigger_overrides_replace_locale_values() -> None:
    catalog = build_command_triggers(
        {
            "menu": CommandTrigger(
                chinese="菜单",
                english="menu",
                chinese_aliases=frozenset(),
                english_aliases=frozenset(),
            )
        },
        {
            "menu": CommandTriggerOverride(
                chinese="功能表",
                english=None,
                chinese_aliases=frozenset({"帮助我"}),
                english_aliases=None,
            )
        },
    )

    assert catalog["menu"].primary_for("zh_CN") == "功能表"
    assert catalog["menu"].aliases_for("zh_CN") == {"帮助我"}
    assert catalog["menu"].primary_for("en_US") == "menu"


def test_command_trigger_overrides_reject_duplicates() -> None:
    defaults = {
        "menu": CommandTrigger("菜单", "menu", frozenset(), frozenset()),
        "member_mute": CommandTrigger("禁言", "mute", frozenset(), frozenset()),
    }

    with pytest.raises(ValueError, match="Duplicate command trigger"):
        build_command_triggers(
            defaults,
            {
                "member_mute": CommandTriggerOverride(
                    chinese="菜单",
                    english=None,
                    chinese_aliases=None,
                    english_aliases=None,
                )
            },
        )
