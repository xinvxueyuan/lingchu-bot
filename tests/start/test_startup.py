from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.start import startup as startup_module


def _empty_registered_adapters(_names: object) -> set[str]:
    return set()


@pytest.mark.asyncio
async def test_startup_imports_group_and_menu_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    group_import = AsyncMock()
    menu_import = AsyncMock(side_effect=lambda: calls.append("menu_import"))

    monkeypatch.setattr(startup_module, "install_schemas", AsyncMock())
    monkeypatch.setattr(startup_module, "ensure_runtime_config_file_async", AsyncMock())
    monkeypatch.setattr(
        startup_module,
        "ensure_menu_config_file_async",
        AsyncMock(side_effect=lambda: calls.append("ensure_menu_config")),
    )
    monkeypatch.setattr(startup_module, "load_bot_state", AsyncMock())
    monkeypatch.setattr(
        startup_module,
        "load_menu_config",
        AsyncMock(
            side_effect=lambda: (
                startup_module.menu_module.MENU_PAGES,
                startup_module.menu_module.MENU_FEATURES,
            )
        ),
    )
    monkeypatch.setattr(
        startup_module.menu_module,
        "set_menu_pages",
        MagicMock(side_effect=lambda _pages: calls.append("set_menu_pages")),
    )
    monkeypatch.setattr(
        startup_module.menu_module,
        "set_menu_features",
        MagicMock(side_effect=lambda _features: calls.append("set_menu_features")),
    )
    monkeypatch.setattr(startup_module, "get_adapters", dict)
    monkeypatch.setattr(
        startup_module,
        "validate_enabled_adapters_loaded",
        MagicMock(),
    )
    monkeypatch.setattr(
        startup_module,
        "resolve_enabled_adapters",
        lambda: {"~onebot.v11"},
    )
    monkeypatch.setattr(
        startup_module,
        "resolve_registered_adapters",
        _empty_registered_adapters,
    )
    monkeypatch.setattr(startup_module, "warm_translation_cache", AsyncMock())
    monkeypatch.setattr(startup_module, "group_import_handle", group_import)
    monkeypatch.setattr(startup_module, "menu_import_handle", menu_import)
    monkeypatch.setattr(
        startup_module,
        "validate_and_seed_permission_system",
        AsyncMock(),
    )
    monkeypatch.setattr(startup_module, "initialize_message_store", AsyncMock())
    monkeypatch.setattr(startup_module, "seed_registry_tables", AsyncMock())

    await startup_module.startup()

    group_import.assert_awaited_once()
    menu_import.assert_awaited_once()
    assert calls.index("ensure_menu_config") < calls.index("menu_import")
    assert calls.index("set_menu_pages") < calls.index("menu_import")
    assert calls.index("set_menu_features") < calls.index("menu_import")
