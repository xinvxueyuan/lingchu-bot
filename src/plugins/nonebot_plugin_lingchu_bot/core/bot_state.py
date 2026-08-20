"""Localstore-backed bot state without third-party model validation."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any

from nonebot import logger, require

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_data_file

from ..database.toml_store import (
    DatabaseError,
    InvalidTOMLRootTypeError,
    TOMLFileReadError,
    load_toml_dict_async,
    write_toml_dict_file_async,
)

_BOT_STATE_FILENAME = "bot_state.toml"
_FLUSH_ATTEMPT_LIMIT = 3


@dataclass(frozen=True, slots=True)
class BotStateGlobal:
    handle_active: bool = True
    silent_mode: bool = False


@dataclass(frozen=True, slots=True)
class BotStatePlatform:
    handle_active: bool | None = None
    silent_mode: bool | None = None


class InvalidBotStateGlobalError(TypeError):
    """Raised when the global bot state is not a mapping."""

    def __init__(self) -> None:
        super().__init__("global bot state must be a mapping")


class InvalidBotStatePlatformsError(TypeError):
    """Raised when platform bot state is not a mapping."""

    def __init__(self) -> None:
        super().__init__("platforms bot state must be a mapping")


class InvalidBotStatePlatformError(TypeError):
    """Raised when one platform state is not a mapping."""

    def __init__(self) -> None:
        super().__init__("platform state must be a mapping")


@dataclass(frozen=True, slots=True)
class BotStateFile:
    global_: BotStateGlobal = field(default_factory=BotStateGlobal)
    platforms: dict[str, BotStatePlatform] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> BotStateFile:
        """Build a typed state model, ignoring invalid scalar values."""
        global_raw = raw.get("global", {})
        if not isinstance(global_raw, dict):
            raise InvalidBotStateGlobalError
        global_state = BotStateGlobal(
            handle_active=_strict_bool(global_raw.get("handle_active"), default=True),
            silent_mode=_strict_bool(global_raw.get("silent_mode"), default=False),
        )
        platforms: dict[str, BotStatePlatform] = {}
        raw_platforms = raw.get("platforms", {})
        if not isinstance(raw_platforms, dict):
            raise InvalidBotStatePlatformsError
        for platform_id, value in raw_platforms.items():
            if not isinstance(value, dict):
                raise InvalidBotStatePlatformError
            platforms[str(platform_id)] = BotStatePlatform(
                handle_active=_optional_bool(value.get("handle_active")),
                silent_mode=_optional_bool(value.get("silent_mode")),
            )
        return cls(global_state, platforms)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "global": asdict(self.global_),
            "platforms": {key: asdict(value) for key, value in self.platforms.items()},
        }


def _strict_bool(value: Any, *, default: bool) -> bool:
    """Return a boolean only for actual TOML booleans."""
    return value if isinstance(value, bool) else default


def _optional_bool(value: Any) -> bool | None:
    """Return a platform override only for actual booleans or ``None``."""
    return value if isinstance(value, bool) else None


_state: dict[str, Any] = {
    "global_handle_active": True,
    "global_silent_mode": False,
    "platforms": {},
}


@dataclass(slots=True)
class _StateCache:
    dirty: bool = False
    persisted_checksum: str | None = None


_cache = _StateCache()
_flush_lock = asyncio.Lock()


def _get_state_file_path() -> Path:
    return get_plugin_data_file(_BOT_STATE_FILENAME)


def _bot_state_defaults() -> dict[str, Any]:
    return BotStateFile().to_mapping()


async def load_bot_state() -> None:
    path = _get_state_file_path()
    default_model = BotStateFile()
    defaults = default_model.to_mapping()
    try:
        data = await load_toml_dict_async(path, default=defaults, merge_default=True)
        model = BotStateFile.from_mapping(data)
    except InvalidTOMLRootTypeError as exc:
        logger.error(
            "Invalid bot state TOML root at {}; using in-memory defaults: {}",
            path,
            exc,
        )
        model = default_model
    except TOMLFileReadError as exc:
        if isinstance(exc.__cause__, OSError):
            logger.error(
                "I/O error reading bot state at {}; using in-memory defaults: {}",
                path,
                exc,
            )
        else:
            logger.error(
                "Invalid bot state TOML at {}; using in-memory defaults: {}",
                path,
                exc,
            )
        model = default_model
    except DatabaseError as exc:
        logger.error(
            "Failed to read bot state from {}; using in-memory defaults: {}",
            path,
            exc,
        )
        model = default_model
    _state["global_handle_active"] = model.global_.handle_active
    _state["global_silent_mode"] = model.global_.silent_mode
    _state["platforms"] = {
        platform_id: {
            key: value for key, value in asdict(platform).items() if value is not None
        }
        for platform_id, platform in model.platforms.items()
    }
    _cache.persisted_checksum = _state_checksum()
    _cache.dirty = False


async def _save_bot_state(state_mapping: dict[str, Any] | None = None) -> None:
    await write_toml_dict_file_async(
        _get_state_file_path(),
        _state_mapping() if state_mapping is None else state_mapping,
    )


def _state_mapping() -> dict[str, Any]:
    return BotStateFile.from_mapping({
        "global": {
            "handle_active": _state["global_handle_active"],
            "silent_mode": _state["global_silent_mode"],
        },
        "platforms": _state["platforms"],
    }).to_mapping()


def _state_checksum(state_mapping: dict[str, Any] | None = None) -> str:
    payload = json.dumps(
        _state_mapping() if state_mapping is None else state_mapping,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _persist_state() -> None:
    _cache.dirty = _state_checksum() != _cache.persisted_checksum


def get_global_handle_active() -> bool:
    return _state["global_handle_active"]


def get_global_silent_mode() -> bool:
    return _state["global_silent_mode"]


def set_global_handle_active(*, active: bool) -> None:
    _state["global_handle_active"] = active
    _persist_state()


def set_global_silent_mode(*, silent: bool) -> None:
    _state["global_silent_mode"] = silent
    _persist_state()


def get_platform_handle_active(platform_id: str) -> bool:
    return _state["platforms"].get(platform_id, {}).get("handle_active", True)


def get_platform_silent_mode(platform_id: str) -> bool:
    return _state["platforms"].get(platform_id, {}).get("silent_mode", False)


def set_platform_handle_active(platform_id: str, *, active: bool) -> None:
    _state["platforms"].setdefault(platform_id, {})["handle_active"] = active
    _persist_state()


def set_platform_silent_mode(platform_id: str, *, silent: bool) -> None:
    _state["platforms"].setdefault(platform_id, {})["silent_mode"] = silent
    _persist_state()


def is_handle_active(platform_id: str) -> bool:
    return _state["global_handle_active"] and get_platform_handle_active(platform_id)


def is_silent_mode(platform_id: str) -> bool:
    return _state["global_silent_mode"] or get_platform_silent_mode(platform_id)


def _reset_state_for_testing() -> None:
    _state["global_handle_active"] = True
    _state["global_silent_mode"] = False
    _state["platforms"] = {}
    _cache.dirty = False
    _cache.persisted_checksum = None


async def flush_bot_state_if_dirty() -> bool:
    """Persist bot state with a stable snapshot and post-write validation."""
    async with _flush_lock:
        flushed = False
        for _attempt in range(_FLUSH_ATTEMPT_LIMIT):
            state_mapping = _state_mapping()
            snapshot_checksum = _state_checksum(state_mapping)
            if not _cache.dirty or snapshot_checksum == _cache.persisted_checksum:
                _cache.dirty = False
                return flushed

            await _save_bot_state(state_mapping)
            _cache.persisted_checksum = snapshot_checksum
            flushed = True

            if _state_checksum() == snapshot_checksum:
                _cache.dirty = False
                return True
            _cache.dirty = True

        logger.warning(
            "Bot state changed during flush; leaving the latest "
            "state dirty after {} attempts",
            _FLUSH_ATTEMPT_LIMIT,
        )
        return flushed


async def reload_bot_state_from_disk() -> None:
    """Reload bot state from disk and replace in-memory state."""
    await load_bot_state()
