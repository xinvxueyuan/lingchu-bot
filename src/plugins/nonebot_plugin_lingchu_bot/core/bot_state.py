"""Two-tier bot state model with TOML persistence.

Maintains a global state plus per-platform overrides for ``handle_active``
and ``silent_mode`` flags. State is persisted to ``bot_state.toml`` in the
plugin data directory.

Resolution semantics:
- ``handle_active``: global AND platform. Global OFF disables all platforms.
- ``silent_mode``: global OR platform. Global ON silences all platforms.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nonebot import logger, require
from nonebot.compat import type_validate_python
from pydantic import BaseModel, ConfigDict, Field, ValidationError

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_data_file

from ..database.toml_store import (
    DatabaseError,
    ensure_toml_dict_file_async,
    load_toml_dict_async,
    write_toml_dict_file_async,
)
from .async_utils import fire_and_forget
from .schemas import BOT_STATE_SCHEMA_BASENAME

_BOT_STATE_FILENAME = "bot_state.toml"


class BotStateGlobal(BaseModel):
    """Global bot state flags shared by every platform."""

    model_config = ConfigDict(extra="ignore")

    handle_active: bool = True
    silent_mode: bool = False


class BotStatePlatform(BaseModel):
    """Per-platform state overrides.

    Fields use ``bool | None = None`` to represent "not set"; the getter
    functions treat a missing key as the default value (``True`` for
    ``handle_active``, ``False`` for ``silent_mode``). ``None`` values
    are stripped before populating the in-memory cache so the existing
    getters continue to work unchanged.
    """

    model_config = ConfigDict(extra="ignore")

    handle_active: bool | None = None
    silent_mode: bool | None = None


class BotStateFile(BaseModel):
    """Two-tier bot state persisted to ``bot_state.toml``.

    The ``global_`` field uses the alias ``"global"`` because ``global``
    is a Python keyword; ``populate_by_name=True`` allows the field to
    be populated by either the alias or the field name during validation.
    Serialization uses ``by_alias=True`` so the TOML file stores
    ``[global]`` rather than ``[global_]``.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    global_: BotStateGlobal = Field(default_factory=BotStateGlobal, alias="global")
    platforms: dict[str, BotStatePlatform] = Field(default_factory=dict)


# In-memory cache (kept for compatibility with existing getters/setters).
# ``platforms`` stores ``dict[str, dict[str, Any]]`` with ``None`` values
# stripped so the existing getters can use ``dict.get(key, default)``.
_state: dict[str, Any] = {
    "global_handle_active": True,
    "global_silent_mode": False,
    "platforms": {},
}


def _get_state_file_path() -> Path:
    """Resolve the path to the bot state TOML file.

    Returns the localstore-managed data file path. Owned by
    ``nonebot_plugin_localstore`` per the ``## Hard Constraints`` rule
    "variable paths must be owned by ``nonebot_plugin_localstore``".
    """
    return get_plugin_data_file(_BOT_STATE_FILENAME)


def _bot_state_defaults() -> dict[str, Any]:
    """Return the default bot state as a JSON-serializable dict (alias form)."""
    return BotStateFile().model_dump(mode="json", by_alias=True)


async def load_bot_state() -> None:
    """Load bot state from TOML file into memory. Called at startup."""
    path = _get_state_file_path()
    defaults = _bot_state_defaults()
    await ensure_toml_dict_file_async(
        path,
        defaults,
        schema_basename=BOT_STATE_SCHEMA_BASENAME,
    )
    try:
        data = await load_toml_dict_async(path, default=defaults, merge_default=True)
        model = type_validate_python(BotStateFile, data)
    except (DatabaseError, ValidationError) as exc:
        logger.error(f"Failed to load bot state, using defaults: {exc}")
        model = BotStateFile()

    global_state = model.global_
    _state["global_handle_active"] = global_state.handle_active
    _state["global_silent_mode"] = global_state.silent_mode
    _state["platforms"] = {
        platform_id: {
            key: value
            for key, value in platform.model_dump(mode="json").items()
            if value is not None
        }
        for platform_id, platform in model.platforms.items()
    }

    logger.info(
        f"Lingchu bot state loaded: handle_active={_state['global_handle_active']}, "
        f"silent_mode={_state['global_silent_mode']}, "
        f"platforms={list(_state['platforms'].keys())}"
    )


async def _save_bot_state() -> None:
    """Persist in-memory state to bot_state.toml."""
    path = _get_state_file_path()
    # ``model_validate`` accepts the ``"global"`` alias (a Python keyword)
    # without requiring a ``global_=`` keyword argument, which pydantic
    # supports at runtime via ``populate_by_name=True`` but pyright cannot
    # statically verify.
    model = BotStateFile.model_validate({
        "global": {
            "handle_active": _state["global_handle_active"],
            "silent_mode": _state["global_silent_mode"],
        },
        "platforms": _state["platforms"],
    })
    try:
        await write_toml_dict_file_async(
            path,
            model.model_dump(mode="json", by_alias=True),
            schema_basename=BOT_STATE_SCHEMA_BASENAME,
        )
    except Exception:
        logger.exception("Failed to save bot state")


def _persist_state() -> None:
    """Fire-and-forget persist state to TOML file."""
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
