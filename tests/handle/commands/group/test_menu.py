from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import patch

import json5
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle import menu
from src.plugins.nonebot_plugin_lingchu_bot.handle.menu import (
    default_menu_store,
    ensure_menu_store,
    load_menu_store,
    menu_cmd,
    render_menu,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.milky.v1_2.default.menu import (
    milkybot_menu,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.onebot.v11.default.menu import (
    onebot11_menu,
)
from tests.handle.commands.group.conftest import finish_text


def test_menu_store_creates_default_json5(tmp_path: Path) -> None:
    config_file = tmp_path / "menu.json5"

    created = ensure_menu_store(config_file)

    assert created == config_file
    loaded = cast(
        "dict[str, Any]", json5.loads(config_file.read_text(encoding="utf-8"))
    )
    assert loaded["version"] == 1
    assert loaded["sections"][0]["title"]["zh_CN"] == "成员管理"


def test_menu_store_does_not_overwrite_existing_file(tmp_path: Path) -> None:
    config_file = tmp_path / "menu.json5"
    config_file.write_text(
        json5.dumps(
            {
                "version": 1,
                "sections": [
                    {
                        "id": "custom",
                        "title": {"zh_CN": "自定义", "en_US": "Custom"},
                        "items": [],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    ensure_menu_store(config_file)
    loaded = load_menu_store(config_file)

    assert loaded["sections"] == [
        {
            "id": "custom",
            "title": {"zh_CN": "自定义", "en_US": "Custom"},
            "items": [],
        }
    ]


def test_render_menu_uses_chinese_triggers(tmp_path: Path) -> None:
    config_file = tmp_path / "menu.json5"
    ensure_menu_store(config_file)

    rendered = render_menu("zh_CN", config_file)

    assert "灵初功能菜单" in rendered
    assert "【成员管理】" in rendered
    assert "- 踢出群成员: 踢出群成员 @用户 [是否拒绝再次申请]" in rendered
    assert "kick-member" not in rendered


def test_render_menu_uses_english_triggers(tmp_path: Path) -> None:
    config_file = tmp_path / "menu.json5"
    ensure_menu_store(config_file)

    rendered = render_menu("en_US", config_file)

    assert "Lingchu Menu" in rendered
    assert "【Member Management】" in rendered
    assert "- Kick a group member: kick-member @user [reject add request]" in rendered
    assert "踢出群成员" not in rendered


def test_render_menu_skips_unknown_command_key(tmp_path: Path) -> None:
    config_file = tmp_path / "menu.json5"
    store = default_menu_store()
    store["sections"] = [
        {
            "id": "broken",
            "title": {"zh_CN": "坏配置", "en_US": "Broken"},
            "items": [
                {
                    "command_key": "unknown_command",
                    "summary": {"zh_CN": "未知", "en_US": "Unknown"},
                    "usage": {"zh_CN": "", "en_US": ""},
                },
                {
                    "command_key": "member_mute",
                    "summary": {"zh_CN": "禁言", "en_US": "Mute"},
                    "usage": {"zh_CN": "@用户", "en_US": "@user"},
                },
            ],
        }
    ]
    config_file.write_text(
        json5.dumps(store, ensure_ascii=False),
        encoding="utf-8",
    )

    rendered = render_menu("zh_CN", config_file)

    assert "未知" not in rendered
    assert "- 禁言: 禁言 @用户" in rendered


@pytest.mark.asyncio
async def test_menu_loader_imports_only_onebot11_modules(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
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
    monkeypatch.setattr(menu, "get_menu_store_file", lambda: tmp_path / "menu.json5")
    menu._loaded_handlers.clear()

    await menu.import_handle()

    assert loaded_modules == [".qq.onebot.v11.default.menu"]
    assert called_handlers == [".qq.onebot.v11.default.menu"]


@pytest.mark.asyncio
async def test_menu_loader_imports_only_milky_modules(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
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
    monkeypatch.setattr(menu, "get_menu_store_file", lambda: tmp_path / "menu.json5")
    menu._loaded_handlers.clear()

    await menu.import_handle()

    assert loaded_modules == [".qq.milky.v1_2.default.menu"]


@pytest.mark.asyncio
async def test_onebot11_menu_finishes_rendered_text() -> None:
    with (
        patch.object(menu_cmd, "finish") as mock_finish,
        patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.qq.onebot.v11.default.menu.render_menu",
            return_value="菜单文本",
        ),
    ):
        await onebot11_menu()

    assert finish_text(mock_finish) == "菜单文本"


@pytest.mark.asyncio
async def test_milky_menu_finishes_rendered_text() -> None:
    with (
        patch.object(menu_cmd, "finish") as mock_finish,
        patch(
            "src.plugins.nonebot_plugin_lingchu_bot.handle.qq.milky.v1_2.default.menu.render_menu",
            return_value="菜单文本",
        ),
    ):
        await milkybot_menu()

    assert finish_text(mock_finish) == "菜单文本"
