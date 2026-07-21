from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands import triggers
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.triggers import (
    CommandTrigger,
    CommandTriggerOverride,
    _is_english_locale,
    _optional_str,
    _optional_str_set,
    _override_from_raw,
    _override_to_json,
    _validate_no_duplicates,
    _validated_primary,
    build_command_triggers,
    delete_command_trigger_override,
    list_command_trigger_overrides,
    upsert_command_trigger_override,
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


def _patch_triggers_toml_helpers(
    monkeypatch: pytest.MonkeyPatch,
    load_return: Any,
) -> tuple[AsyncMock, AsyncMock]:
    if isinstance(load_return, Exception):
        load_mock = AsyncMock(side_effect=load_return)
    else:
        load_mock = AsyncMock(return_value=load_return)
    write_mock = AsyncMock()
    monkeypatch.setattr(triggers, "load_toml_dict_async", load_mock)
    monkeypatch.setattr(triggers, "write_toml_dict_file_async", write_mock)
    return load_mock, write_mock


def test_build_command_triggers_skips_override_for_unknown_command_key() -> None:
    defaults = {"menu": CommandTrigger("菜单", "menu", frozenset(), frozenset())}

    catalog = build_command_triggers(
        defaults,
        {"unknown_command": CommandTriggerOverride(chinese="未知")},
    )

    assert catalog == defaults
    assert catalog["menu"].chinese == "菜单"


def test_validated_primary_returns_fallback_when_value_is_none() -> None:
    assert _validated_primary(None, "菜单") == "菜单"


def test_validated_primary_strips_surrounding_whitespace() -> None:
    assert _validated_primary("  功能表  ", "菜单") == "功能表"


def test_validated_primary_raises_on_whitespace_only_value() -> None:
    with pytest.raises(ValueError, match="Command trigger primary cannot be empty"):
        _validated_primary("   ", "菜单")


def test_validate_no_duplicates_skips_empty_values() -> None:
    catalog = {
        "menu": CommandTrigger("", "menu", frozenset({""}), frozenset()),
        "kick": CommandTrigger("", "kick", frozenset({""}), frozenset()),
    }

    _validate_no_duplicates(catalog)


def test_validate_no_duplicates_raises_on_cross_command_alias_conflict() -> None:
    defaults = {
        "menu": CommandTrigger("菜单", "menu", frozenset({"踢出"}), frozenset()),
        "kick": CommandTrigger("踢出", "kick", frozenset(), frozenset()),
    }

    with pytest.raises(ValueError, match="Duplicate command trigger"):
        build_command_triggers(defaults, {})


def test_primary_for_returns_english_for_english_locale() -> None:
    trigger = CommandTrigger("菜单", "menu", frozenset({"帮助"}), frozenset({"help"}))

    assert trigger.primary_for("en_US") == "menu"
    assert trigger.aliases_for("en_US") == {"help"}


def test_primary_for_returns_chinese_for_non_english_locale() -> None:
    trigger = CommandTrigger("菜单", "menu", frozenset({"帮助"}), frozenset({"help"}))

    assert trigger.primary_for("zh_CN") == "菜单"
    assert trigger.aliases_for("zh_CN") == {"帮助"}


def test_primary_and_aliases_properties_use_configured_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trigger = CommandTrigger("菜单", "menu", frozenset({"帮助"}), frozenset({"help"}))

    monkeypatch.setattr(triggers, "get_configured_locale", lambda: "zh_CN")
    assert trigger.primary == "菜单"
    assert trigger.aliases == {"帮助"}

    monkeypatch.setattr(triggers, "get_configured_locale", lambda: "en_US")
    assert trigger.primary == "menu"
    assert trigger.aliases == {"help"}


def test_is_english_locale_falls_back_to_configured_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(triggers, "get_configured_locale", lambda: "en_US")
    assert _is_english_locale(None) is True

    monkeypatch.setattr(triggers, "get_configured_locale", lambda: "zh_CN")
    assert _is_english_locale(None) is False


def test_override_from_raw_returns_default_when_not_dict() -> None:
    assert _override_from_raw("not a dict") == CommandTriggerOverride()
    assert _override_from_raw(None) == CommandTriggerOverride()


def test_override_from_raw_builds_override_from_dict() -> None:
    result = _override_from_raw({
        "chinese": "功能表",
        "english": "my-menu",
        "chinese_aliases": ["帮助我", "  "],
        "english_aliases": ("help-me",),
    })

    assert result == CommandTriggerOverride(
        chinese="功能表",
        english="my-menu",
        chinese_aliases=frozenset({"帮助我"}),
        english_aliases=frozenset({"help-me"}),
    )


def test_optional_str_returns_none_for_none() -> None:
    assert _optional_str(None) is None


def test_optional_str_coerces_non_str_value() -> None:
    assert _optional_str(123) == "123"
    assert _optional_str("功能表") == "功能表"


def test_optional_str_set_returns_none_for_none() -> None:
    assert _optional_str_set(None) is None


def test_optional_str_set_returns_none_for_non_iterable_type() -> None:
    assert _optional_str_set("not a list") is None
    assert _optional_str_set(42) is None


def test_optional_str_set_returns_frozenset_stripping_and_filtering() -> None:
    assert _optional_str_set(["a", " b ", ""]) == frozenset({"a", "b"})
    assert _optional_str_set(("x",)) == frozenset({"x"})


def test_override_to_json_serializes_full_override() -> None:
    override = CommandTriggerOverride(
        chinese="功能表",
        english="my-menu",
        chinese_aliases=frozenset({"帮助我"}),
        english_aliases=frozenset({"help-me"}),
    )

    assert _override_to_json(override) == {
        "chinese": "功能表",
        "english": "my-menu",
        "chinese_aliases": ["帮助我"],
        "english_aliases": ["help-me"],
    }


def test_override_to_json_omits_none_fields() -> None:
    assert _override_to_json(CommandTriggerOverride()) == {}


@pytest.mark.asyncio
async def test_list_command_trigger_overrides_returns_empty_when_raw_not_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_mock, write_mock = _patch_triggers_toml_helpers(
        monkeypatch, load_return={"command_trigger_overrides": ["not", "a", "dict"]}
    )

    assert await list_command_trigger_overrides() == {}
    load_mock.assert_awaited_once()
    write_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_command_trigger_overrides_parses_dict_raw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = {"menu": {"chinese": "功能表", "english_aliases": ["help-me"]}}
    load_mock, write_mock = _patch_triggers_toml_helpers(
        monkeypatch, load_return={"command_trigger_overrides": raw}
    )

    result = await list_command_trigger_overrides()

    assert set(result) == {"menu"}
    assert result["menu"] == CommandTriggerOverride(
        chinese="功能表",
        english_aliases=frozenset({"help-me"}),
    )
    load_mock.assert_awaited_once()
    write_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_upsert_command_trigger_override_merges_and_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_mock, write_mock = _patch_triggers_toml_helpers(monkeypatch, load_return={})
    override = CommandTriggerOverride(
        chinese="我的菜单",
        english="my-menu",
        chinese_aliases=frozenset({"我的帮助"}),
        english_aliases=frozenset({"my-help"}),
    )

    result = await upsert_command_trigger_override("menu", override)

    assert result["menu"] == override
    load_mock.assert_awaited()
    write_mock.assert_awaited_once()
    written_data = write_mock.call_args.args[1]
    assert written_data["command_trigger_overrides"]["menu"] == {
        "chinese": "我的菜单",
        "english": "my-menu",
        "chinese_aliases": ["我的帮助"],
        "english_aliases": ["my-help"],
    }


@pytest.mark.asyncio
async def test_delete_command_trigger_override_returns_db_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = {"menu": {"chinese": "功能表", "english_aliases": ["help-me"]}}
    load_mock, write_mock = _patch_triggers_toml_helpers(
        monkeypatch, load_return={"command_trigger_overrides": raw}
    )

    assert await delete_command_trigger_override("menu") is True
    load_mock.assert_awaited_once()
    write_mock.assert_awaited_once()
    written_data = write_mock.call_args.args[1]
    assert "menu" not in written_data["command_trigger_overrides"]


@pytest.mark.asyncio
async def test_delete_command_trigger_override_returns_false_when_key_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_mock, write_mock = _patch_triggers_toml_helpers(
        monkeypatch, load_return={"command_trigger_overrides": {}}
    )

    assert await delete_command_trigger_override("unknown") is False
    load_mock.assert_awaited_once()
    write_mock.assert_not_awaited()
