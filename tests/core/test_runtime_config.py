from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import runtime_config


@pytest.mark.asyncio
async def test_load_runtime_configs_on_startup_loads_all_domains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_bot_state = AsyncMock()
    load_menu_config = AsyncMock(
        return_value=(
            runtime_config.menu_module._DEFAULT_MENU_PAGES,
            runtime_config.menu_module._DEFAULT_MENU_FEATURES,
        )
    )
    set_menu_pages = MagicMock()
    set_menu_features = MagicMock()
    manager = MagicMock()
    manager.get_all_configs = AsyncMock()
    load_mutable_settings = AsyncMock()

    monkeypatch.setattr(runtime_config, "load_bot_state", load_bot_state)
    monkeypatch.setattr(runtime_config, "load_menu_config", load_menu_config)
    monkeypatch.setattr(runtime_config.menu_module, "set_menu_pages", set_menu_pages)
    monkeypatch.setattr(
        runtime_config.menu_module,
        "set_menu_features",
        set_menu_features,
    )
    monkeypatch.setattr(runtime_config, "get_handle_config_manager", lambda: manager)
    monkeypatch.setattr(
        runtime_config,
        "load_mutable_settings",
        load_mutable_settings,
    )

    await runtime_config.load_runtime_configs_on_startup()

    load_bot_state.assert_awaited_once()
    load_menu_config.assert_awaited_once()
    set_menu_pages.assert_called_once()
    set_menu_features.assert_called_once()
    manager.get_all_configs.assert_awaited_once()
    load_mutable_settings.assert_awaited_once()


@pytest.mark.asyncio
async def test_load_runtime_configs_on_startup_falls_back_when_menu_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_error = MagicMock()
    monkeypatch.setattr(runtime_config.logger, "error", log_error)
    monkeypatch.setattr(
        runtime_config,
        "load_menu_config",
        AsyncMock(
            side_effect=runtime_config.MenuConfigError(
                Path("menu.toml"),
                ValueError("invalid menu"),
            )
        ),
    )
    monkeypatch.setattr(runtime_config, "load_bot_state", AsyncMock())
    manager = MagicMock()
    manager.get_all_configs = AsyncMock()
    monkeypatch.setattr(runtime_config, "get_handle_config_manager", lambda: manager)
    monkeypatch.setattr(runtime_config, "load_mutable_settings", AsyncMock())

    set_menu_pages = MagicMock()
    set_menu_features = MagicMock()
    monkeypatch.setattr(runtime_config.menu_module, "set_menu_pages", set_menu_pages)
    monkeypatch.setattr(
        runtime_config.menu_module,
        "set_menu_features",
        set_menu_features,
    )

    await runtime_config.load_runtime_configs_on_startup()

    log_error.assert_called_once()
    set_menu_pages.assert_called_once_with(
        runtime_config.menu_module._DEFAULT_MENU_PAGES
    )
    set_menu_features.assert_called_once_with(
        runtime_config.menu_module._DEFAULT_MENU_FEATURES
    )


@pytest.mark.asyncio
async def test_reload_runtime_configs_from_disk_clears_cache_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager = MagicMock()
    manager.clear_cache = MagicMock()
    monkeypatch.setattr(runtime_config, "get_handle_config_manager", lambda: manager)
    load_runtime = AsyncMock()
    monkeypatch.setattr(
        runtime_config,
        "load_runtime_configs_on_startup",
        load_runtime,
    )

    await runtime_config.reload_runtime_configs_from_disk()

    manager.clear_cache.assert_called_once()
    load_runtime.assert_awaited_once()


@pytest.mark.asyncio
async def test_flush_runtime_configs_on_shutdown_flushes_dirty_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flush_bot_state = AsyncMock(return_value=True)
    flush_mutable = AsyncMock(return_value=False)
    monkeypatch.setattr(runtime_config, "flush_bot_state_if_dirty", flush_bot_state)
    monkeypatch.setattr(
        runtime_config,
        "flush_mutable_settings_if_dirty",
        flush_mutable,
    )

    result = await runtime_config.flush_runtime_configs_on_shutdown()

    flush_bot_state.assert_awaited_once()
    flush_mutable.assert_awaited_once()
    assert result == (True, False)
