"""Localstore-backed bot state without third-party model validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from nonebot import logger, require

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_data_file

from ..database.toml_store import (
    DatabaseError,
    ensure_toml_dict_file_async,
    load_toml_dict_async,
    write_toml_dict_file_async,
)
from .async_utils import fire_and_forget

_BOT_STATE_FILENAME = "bot_state.toml"


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
        global_raw = raw.get("global", {})
        if not isinstance(global_raw, dict):
            raise InvalidBotStateGlobalError
        global_state = BotStateGlobal(
            handle_active=bool(global_raw.get("handle_active", True)),
            silent_mode=bool(global_raw.get("silent_mode", False)),
        )
        platforms: dict[str, BotStatePlatform] = {}
        raw_platforms = raw.get("platforms", {})
        if not isinstance(raw_platforms, dict):
            raise InvalidBotStatePlatformsError
        for platform_id, value in raw_platforms.items():
            if not isinstance(value, dict):
                raise InvalidBotStatePlatformError
            platforms[str(platform_id)] = BotStatePlatform(
                handle_active=value.get("handle_active"),
                silent_mode=value.get("silent_mode"),
            )
        return cls(global_state, platforms)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "global": asdict(self.global_),
            "platforms": {key: asdict(value) for key, value in self.platforms.items()},
        }


_state: dict[str, Any] = {
    "global_handle_active": True,
    "global_silent_mode": False,
    "platforms": {},
}


def _get_state_file_path() -> Path:
    return get_plugin_data_file(_BOT_STATE_FILENAME)


def _bot_state_defaults() -> dict[str, Any]:
    return BotStateFile().to_mapping()


async def load_bot_state() -> None:
    path = _get_state_file_path()
    defaults = _bot_state_defaults()
    await ensure_toml_dict_file_async(path, defaults)
    try:
        data = await load_toml_dict_async(path, default=defaults, merge_default=True)
        model = BotStateFile.from_mapping(data)
    except (DatabaseError, ValueError) as exc:
        logger.error("Failed to load bot state, using defaults: {}", exc)
        model = BotStateFile()
    _state["global_handle_active"] = model.global_.handle_active
    _state["global_silent_mode"] = model.global_.silent_mode
    _state["platforms"] = {
        platform_id: {
            key: value for key, value in asdict(platform).items() if value is not None
        }
        for platform_id, platform in model.platforms.items()
    }


async def _save_bot_state() -> None:
    try:
        await write_toml_dict_file_async(
            _get_state_file_path(),
            BotStateFile.from_mapping({
                "global": {
                    "handle_active": _state["global_handle_active"],
                    "silent_mode": _state["global_silent_mode"],
                },
                "platforms": _state["platforms"],
            }).to_mapping(),
        )
    except Exception:
        logger.exception("Failed to save bot state")


def _persist_state() -> None:
    fire_and_forget(_save_bot_state(), name="save_bot_state")


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
