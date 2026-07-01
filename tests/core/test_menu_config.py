"""Tests for :mod:`core.menu_config` JSON5-backed menu configuration."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import aiofiles
import json5
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core.menu_config import (
    MENU_CONFIG_VERSION,
    MENU_FILENAME,
    MenuConfigError,
    ensure_menu_config_file_async,
    get_menu_config_file,
    load_menu_config,
    menu_config_defaults,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.schemas import (
    MENU_SCHEMA_BASENAME,
    MENU_SCHEMA_TEXT,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle import menu as menu_module
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.commands.triggers import (
    COMMAND_TRIGGERS,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_menu_config_defaults_returns_all_known_feature_command_keys() -> None:
    defaults = menu_config_defaults()
    command_keys = _command_keys_from_pages(defaults["pages"])

    assert command_keys == {
        feature.command_key for feature in menu_module._DEFAULT_MENU_FEATURES
    }
    assert command_keys <= set(COMMAND_TRIGGERS)


def test_menu_config_defaults_returns_all_known_page_ids() -> None:
    defaults = menu_config_defaults()

    assert _page_ids_from_pages(defaults["pages"]) == {
        page.id for page in _flatten_pages(menu_module._DEFAULT_MENU_PAGES)
    }


def test_menu_config_defaults_contain_schema_and_version() -> None:
    defaults = menu_config_defaults()

    assert defaults["$schema"] == MENU_SCHEMA_BASENAME
    assert defaults["version"] == MENU_CONFIG_VERSION


def test_menu_config_defaults_excludes_runtime_fields() -> None:
    defaults = menu_config_defaults()

    for entry in _walk_page_dicts(defaults["pages"]):
        assert "platform_capability" not in entry
        assert "availability" not in entry
        assert "section_id" not in entry


def test_mass_announcement_menu_feature_is_remote_announcement_capability() -> None:
    feature = _feature_by_key(menu_module._DEFAULT_MENU_FEATURES, "mass_announcement")

    assert feature.section_id == "remote-management"
    assert feature.platform_capability == menu_module.PlatformCapability.ANNOUNCEMENT
    assert feature.availability == menu_module._ONEBOT_ANNOUNCEMENT


def test_restart_protocol_endpoint_menu_feature_is_application_operation() -> None:
    page = next(
        page
        for page in menu_module._DEFAULT_MENU_PAGES
        if page.id == "system-management"
    )
    assert any(child.id == "application-operation" for child in page.children)

    feature = _feature_by_key(
        menu_module._DEFAULT_MENU_FEATURES, "restart_protocol_endpoint"
    )
    assert feature.section_id == "application-operation"
    assert (
        feature.platform_capability
        == menu_module.PlatformCapability.APPLICATION_OPERATION
    )


def test_menu_config_defaults_have_schema_compatible_shape() -> None:
    schema = json.loads(MENU_SCHEMA_TEXT)
    defaults = menu_config_defaults()

    assert schema["properties"]["pages"]["type"] == "array"
    assert isinstance(defaults["pages"], list)
    assert all({"id", "title"} <= set(page) for page in defaults["pages"])


def test_get_menu_config_file_falls_back_when_localstore_has_no_plugin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "src.plugins.nonebot_plugin_lingchu_bot.core.menu_config.get_plugin_config_file",
        lambda _filename: (_ for _ in ()).throw(ValueError("no plugin")),
    )

    assert get_menu_config_file().name == MENU_FILENAME


async def test_load_menu_config_falls_back_when_file_missing(tmp_path: Path) -> None:
    pages, features = await load_menu_config(tmp_path / "missing.json5")

    assert pages == menu_module._DEFAULT_MENU_PAGES
    assert features == menu_module._DEFAULT_MENU_FEATURES


async def test_load_menu_config_overrides_summary(tmp_path: Path) -> None:
    config_file = tmp_path / "menu.json5"
    payload = menu_config_defaults()
    payload["pages"][0]["items"] = [
        {
            "command_key": "kick_member",
            "summary": {"zh_CN": "踢人", "en_US": "Kick a group member"},
            "usage": {"zh_CN": "@用户", "en_US": "@user"},
        }
    ]
    async with aiofiles.open(config_file, "w", encoding="utf-8") as f:
        await f.write(json5.dumps(payload, ensure_ascii=False))

    _, features = await load_menu_config(config_file)
    loaded = _feature_by_key(features, "kick_member")
    default = _feature_by_key(menu_module._DEFAULT_MENU_FEATURES, "kick_member")

    assert loaded.summary.zh_cn == "踢人"
    assert loaded.platform_capability == default.platform_capability
    assert loaded.availability == default.availability


async def test_load_menu_config_preserves_json5_item_order(tmp_path: Path) -> None:
    config_file = tmp_path / "menu.json5"
    payload = menu_config_defaults()
    payload["pages"][0]["items"] = [
        _menu_item("set_member_card"),
        _menu_item("kick_member"),
    ]
    async with aiofiles.open(config_file, "w", encoding="utf-8") as f:
        await f.write(json5.dumps(payload, ensure_ascii=False))

    _, features = await load_menu_config(config_file)

    assert [feature.command_key for feature in features[:2]] == [
        "set_member_card",
        "kick_member",
    ]


async def test_load_menu_config_does_not_override_page_command(tmp_path: Path) -> None:
    config_file = tmp_path / "menu.json5"
    payload = menu_config_defaults()
    payload["pages"][0]["command"] = {"zh_CN": "成员", "en_US": "members"}
    async with aiofiles.open(config_file, "w", encoding="utf-8") as f:
        await f.write(json5.dumps(payload, ensure_ascii=False))

    pages, _ = await load_menu_config(config_file)

    assert pages[0].command == menu_module._DEFAULT_MENU_PAGES[0].command


async def test_load_menu_config_rejects_unknown_command_key(tmp_path: Path) -> None:
    config_file = tmp_path / "menu.json5"
    payload = menu_config_defaults()
    payload["pages"][0]["items"] = [
        {
            "command_key": "nonexistent_cmd",
            "summary": {"zh_CN": "不存在", "en_US": "Missing"},
            "usage": {"zh_CN": "", "en_US": ""},
        }
    ]
    async with aiofiles.open(config_file, "w", encoding="utf-8") as f:
        await f.write(json5.dumps(payload, ensure_ascii=False))

    with pytest.raises(MenuConfigError) as exc_info:
        await load_menu_config(config_file)

    message = str(exc_info.value)
    assert "nonexistent_cmd" in message
    assert str(config_file) in message


async def test_load_menu_config_rejects_unsupported_version(tmp_path: Path) -> None:
    config_file = tmp_path / "menu.json5"
    payload = menu_config_defaults()
    payload["version"] = 999
    async with aiofiles.open(config_file, "w", encoding="utf-8") as f:
        await f.write(json5.dumps(payload, ensure_ascii=False))

    with pytest.raises(MenuConfigError, match="unsupported menu config version"):
        await load_menu_config(config_file)


async def test_load_menu_config_warns_unknown_page_id(tmp_path: Path) -> None:
    config_file = tmp_path / "menu.json5"
    payload = menu_config_defaults()
    payload["pages"].insert(
        0,
        {"id": "unknown-page", "title": {"zh_CN": "未知", "en_US": "Unknown"}},
    )
    async with aiofiles.open(config_file, "w", encoding="utf-8") as f:
        await f.write(json5.dumps(payload, ensure_ascii=False))

    with patch(
        "src.plugins.nonebot_plugin_lingchu_bot.core.menu_config.logger.warning"
    ) as mock_warning:
        pages, _ = await load_menu_config(config_file)

    assert "unknown-page" not in {page.id for page in pages}
    assert {page.id for page in pages} >= {"member-management", "system-management"}
    mock_warning.assert_called_once()
    assert "unknown-page" in str(mock_warning.call_args)


@pytest.mark.asyncio
async def test_ensure_menu_config_file_async_creates_then_idempotent(
    tmp_path: Path,
) -> None:
    config_file = tmp_path / "menu.json5"

    created = await ensure_menu_config_file_async(config_file)
    async with aiofiles.open(config_file, encoding="utf-8") as f:
        first_content = await f.read()
    async with aiofiles.open(config_file, "w", encoding="utf-8") as f:
        await f.write("{version: 2, pages: []}")
    second = await ensure_menu_config_file_async(config_file)

    assert created == config_file
    assert second == config_file
    assert MENU_SCHEMA_BASENAME in first_content
    async with aiofiles.open(config_file, encoding="utf-8") as f:
        assert await f.read() == "{version: 2, pages: []}"


def _feature_by_key(
    features: tuple[menu_module.MenuFeature, ...],
    command_key: str,
) -> menu_module.MenuFeature:
    return next(feature for feature in features if feature.command_key == command_key)


def _menu_item(command_key: str) -> dict[str, Any]:
    feature = _feature_by_key(menu_module._DEFAULT_MENU_FEATURES, command_key)
    return {
        "command_key": command_key,
        "summary": {"zh_CN": feature.summary.zh_cn, "en_US": feature.summary.en_us},
        "usage": {"zh_CN": feature.usage.zh_cn, "en_US": feature.usage.en_us},
    }


def _command_keys_from_pages(pages: list[dict[str, Any]]) -> set[str]:
    result: set[str] = set()
    for page in pages:
        result.update(str(item["command_key"]) for item in page.get("items", []))
        result.update(_command_keys_from_pages(page.get("children", [])))
    return result


def _page_ids_from_pages(pages: list[dict[str, Any]]) -> set[str]:
    result: set[str] = set()
    for page in pages:
        result.add(str(page["id"]))
        result.update(_page_ids_from_pages(page.get("children", [])))
    return result


def _walk_page_dicts(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for page in pages:
        result.append(page)
        result.extend(page.get("items", []))
        result.extend(_walk_page_dicts(page.get("children", [])))
    return result


def _flatten_pages(
    pages: tuple[menu_module.MenuPage, ...],
) -> tuple[menu_module.MenuPage, ...]:
    result: list[menu_module.MenuPage] = []
    for page in pages:
        result.append(page)
        result.extend(_flatten_pages(page.children))
    return tuple(result)
