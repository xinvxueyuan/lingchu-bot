"""Two-tier bot state model with JSON5 persistence.

Maintains a global state plus per-platform overrides for ``handle_active``
and ``silent_mode`` flags. State is persisted to ``bot_state.json5`` in the
plugin data directory.

Resolution semantics:
- ``handle_active``: global AND platform. Global OFF disables all platforms.
- ``silent_mode``: global OR platform. Global ON silences all platforms.
"""

from pathlib import Path
from typing import Any

from nonebot import logger, require

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_data_file

from ..database.json5_store import (
    ensure_json5_dict_file_async,
    load_json5_dict_async,
    write_json5_dict_file_async,
)
from .async_utils import fire_and_forget
from .schemas import BOT_STATE_SCHEMA_BASENAME

_BOT_STATE_FILENAME = "bot_state.json5"

_DEFAULT_STATE: dict[str, Any] = {
    "$schema": BOT_STATE_SCHEMA_BASENAME,
    "global": {
        "handle_active": True,
        "silent_mode": False,
    },
    "platforms": {},
}

_state: dict[str, Any] = {
    "global_handle_active": True,
    "global_silent_mode": False,
    "platforms": {},
    "$schema": BOT_STATE_SCHEMA_BASENAME,
}


def _get_state_file_path() -> Path:
    """Resolve the path to the bot state JSON5 file.

    Returns the localstore-managed data file path. Owned by
    ``nonebot_plugin_localstore`` per the ``## Hard Constraints`` rule
    "variable paths must be owned by ``nonebot_plugin_localstore``".
    """
    return get_plugin_data_file(_BOT_STATE_FILENAME)


async def load_bot_state() -> None:
    """Load bot state from JSON5 file into memory. Called at startup."""
    path = _get_state_file_path()
    await ensure_json5_dict_file_async(path, _DEFAULT_STATE)
    data = await load_json5_dict_async(path, default=_DEFAULT_STATE, merge_default=True)

    global_state = data.get("global", {})
    _state["global_handle_active"] = global_state.get("handle_active", True)
    _state["global_silent_mode"] = global_state.get("silent_mode", False)

    platforms = data.get("platforms", {})
    _state["platforms"] = platforms if isinstance(platforms, dict) else {}

    logger.info(
        f"Lingchu bot state loaded: handle_active={_state['global_handle_active']}, "
        f"silent_mode={_state['global_silent_mode']}, "
        f"platforms={list(_state['platforms'].keys())}"
    )


async def _save_bot_state() -> None:
    """Persist in-memory state to bot_state.json5."""
    path = _get_state_file_path()
    schema_value = _state.get("$schema") or BOT_STATE_SCHEMA_BASENAME
    data = {
        "$schema": schema_value,
        "global": {
            "handle_active": _state["global_handle_active"],
            "silent_mode": _state["global_silent_mode"],
        },
        "platforms": _state["platforms"],
    }
    try:
        await write_json5_dict_file_async(path, data)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to save bot state")


def _persist_state() -> None:
    """Fire-and-forget persist state to JSON5 file."""
    fire_and_forget(_save_bot_state(), name="save_bot_state")


def get_global_handle_active() -> bool:
    """Return the global handle-active flag."""
    return _state["global_handle_active"]


def get_global_silent_mode() -> bool:
    """Return the global silent-mode flag."""
    return _state["global_silent_mode"]


def set_global_handle_active(*, active: bool) -> None:
    """Set the global handle-active flag and persist."""
    _state["global_handle_active"] = active
    _persist_state()


def set_global_silent_mode(*, silent: bool) -> None:
    """Set the global silent-mode flag and persist."""
    _state["global_silent_mode"] = silent
    _persist_state()


def get_platform_handle_active(platform_id: str) -> bool:
    """Return the per-platform handle-active flag (default True)."""
    platform = _state["platforms"].get(platform_id, {})
    return platform.get("handle_active", True)


def get_platform_silent_mode(platform_id: str) -> bool:
    """Return the per-platform silent-mode flag (default False)."""
    platform = _state["platforms"].get(platform_id, {})
    return platform.get("silent_mode", False)


def set_platform_handle_active(platform_id: str, *, active: bool) -> None:
    """Set the per-platform handle-active flag and persist."""
    if platform_id not in _state["platforms"]:
        _state["platforms"][platform_id] = {}
    _state["platforms"][platform_id]["handle_active"] = active
    _persist_state()


def set_platform_silent_mode(platform_id: str, *, silent: bool) -> None:
    """Set the per-platform silent-mode flag and persist."""
    if platform_id not in _state["platforms"]:
        _state["platforms"][platform_id] = {}
    _state["platforms"][platform_id]["silent_mode"] = silent
    _persist_state()


def is_handle_active(platform_id: str) -> bool:
    """Resolve handle-active: global AND platform. Global OFF -> all OFF."""
    if not _state["global_handle_active"]:
        return False
    return get_platform_handle_active(platform_id)


def is_silent_mode(platform_id: str) -> bool:
    """Resolve silent-mode: global OR platform. Global ON -> all silent."""
    if _state["global_silent_mode"]:
        return True
    return get_platform_silent_mode(platform_id)


def _reset_state_for_testing() -> None:
    """Reset state to defaults. For test fixtures only."""
    _state["global_handle_active"] = True
    _state["global_silent_mode"] = False
    _state["platforms"] = {}
    _state["$schema"] = BOT_STATE_SCHEMA_BASENAME
