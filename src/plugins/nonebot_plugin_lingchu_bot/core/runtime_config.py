"""Runtime TOML config lifecycle: startup load, reload, and dirty flush."""

from __future__ import annotations

import asyncio

from nonebot import logger

from ..database.toml_store import DatabaseError
from ..handle import menu as menu_module
from .bot_state import flush_bot_state_if_dirty, load_bot_state
from .config import get_handle_config_manager
from .menu_config import MenuConfigError, load_menu_config
from .mutable_settings import (
    MutableSettingsError,
    flush_mutable_settings_if_dirty,
    load_mutable_settings,
    reset_mutable_settings_cache,
)


async def load_runtime_configs_on_startup() -> None:
    """Load TOML runtime configs into memory cache on startup."""
    await load_bot_state()
    await _load_menu_runtime()
    manager = get_handle_config_manager()
    await manager.get_all_configs()
    try:
        await load_mutable_settings()
    except MutableSettingsError as exc:
        reset_mutable_settings_cache()
        logger.error(
            "Failed to load mutable settings; using in-memory defaults: {}",
            exc,
        )


async def reload_runtime_configs_from_disk() -> None:
    """Force reload runtime TOML configs from disk into memory."""
    manager = get_handle_config_manager()
    manager.clear_cache()
    await load_runtime_configs_on_startup()


async def flush_runtime_configs_on_shutdown() -> tuple[bool, bool]:
    """Flush dirty runtime TOML configs to disk before process exits."""
    bot_state_flushed = False
    mutable_settings_flushed = False
    first_error: BaseException | None = None
    try:
        bot_state_flushed = await flush_bot_state_if_dirty()
    except asyncio.CancelledError as exc:
        first_error = exc
    except (DatabaseError, MutableSettingsError, OSError) as exc:
        first_error = exc
    try:
        mutable_settings_flushed = await flush_mutable_settings_if_dirty()
    except asyncio.CancelledError as exc:
        first_error = first_error or exc
    except (DatabaseError, MutableSettingsError, OSError) as exc:
        first_error = first_error or exc
    if first_error is not None:
        raise first_error
    return (bot_state_flushed, mutable_settings_flushed)


async def _load_menu_runtime() -> None:
    try:
        menu_pages, menu_features = await load_menu_config()
        menu_module.set_menu_pages(menu_pages)
        menu_module.set_menu_features(menu_features)
    except MenuConfigError as exc:
        logger.error(
            "Failed to load menu config; using in-memory defaults: {}",
            exc,
        )
        menu_module.set_menu_pages(menu_module._DEFAULT_MENU_PAGES)
        menu_module.set_menu_features(menu_module._DEFAULT_MENU_FEATURES)
