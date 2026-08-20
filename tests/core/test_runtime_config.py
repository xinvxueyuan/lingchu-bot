from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from _lingchu_bot_contracts import MutableRuntimeSettings
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import (
    mutable_settings as settings_module,
    runtime_config,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.toml_store import DatabaseError


@pytest.fixture(autouse=True)
def clear_mutable_settings_cache() -> Iterator[None]:
    settings_module._cache.value = None
    settings_module._cache.dirty = False
    settings_module._cache.persisted_checksum = None
    yield
    settings_module._cache.value = None
    settings_module._cache.dirty = False
    settings_module._cache.persisted_checksum = None


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
async def test_load_runtime_configs_on_startup_resets_mutable_defaults_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale_settings = MutableRuntimeSettings(
        permission_platform_runtime_passthrough=False,
    )
    settings_module._cache.value = stale_settings
    settings_module._cache.dirty = True
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
    load_error = runtime_config.MutableSettingsError("broken settings")
    load_mutable_settings = AsyncMock(side_effect=load_error)
    log_error = MagicMock()

    monkeypatch.setattr(runtime_config, "load_bot_state", load_bot_state)
    monkeypatch.setattr(runtime_config, "load_menu_config", load_menu_config)
    monkeypatch.setattr(runtime_config.menu_module, "set_menu_pages", set_menu_pages)
    monkeypatch.setattr(
        runtime_config.menu_module,
        "set_menu_features",
        set_menu_features,
    )
    monkeypatch.setattr(runtime_config, "get_handle_config_manager", lambda: manager)
    monkeypatch.setattr(runtime_config, "load_mutable_settings", load_mutable_settings)
    monkeypatch.setattr(runtime_config.logger, "error", log_error)

    await runtime_config.load_runtime_configs_on_startup()

    assert settings_module._cache.value == MutableRuntimeSettings()
    assert settings_module._cache.dirty is False
    load_bot_state.assert_awaited_once()
    load_menu_config.assert_awaited_once()
    set_menu_pages.assert_called_once()
    set_menu_features.assert_called_once()
    manager.get_all_configs.assert_awaited_once()
    load_mutable_settings.assert_awaited_once()
    log_error.assert_called_once_with(
        "Failed to load mutable settings; using in-memory defaults: {}",
        load_error,
    )


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


@pytest.mark.parametrize(
    ("failing", "expected_exception", "expected_message"),
    [
        pytest.param("bot", DatabaseError, "bot state failed"),
        pytest.param("bot_oserror", OSError, "bot state failed"),
        pytest.param(
            "mutable",
            runtime_config.MutableSettingsError,
            "mutable settings failed",
        ),
    ],
)
@pytest.mark.asyncio
async def test_flush_runtime_configs_on_shutdown_attempts_both_domains(
    monkeypatch: pytest.MonkeyPatch,
    failing: str,
    expected_exception: type[BaseException],
    expected_message: str,
) -> None:
    call_order: list[str] = []

    async def flush_bot_state() -> bool:
        call_order.append("bot")
        if failing == "bot":
            raise DatabaseError("bot state failed")
        if failing == "bot_oserror":
            raise OSError("bot state failed")
        return True

    async def flush_mutable_settings() -> bool:
        call_order.append("mutable")
        if failing == "mutable":
            raise runtime_config.MutableSettingsError("mutable settings failed")
        return True

    monkeypatch.setattr(runtime_config, "flush_bot_state_if_dirty", flush_bot_state)
    monkeypatch.setattr(
        runtime_config,
        "flush_mutable_settings_if_dirty",
        flush_mutable_settings,
    )

    with pytest.raises(expected_exception, match=expected_message):
        await runtime_config.flush_runtime_configs_on_shutdown()

    assert call_order == ["bot", "mutable"]
