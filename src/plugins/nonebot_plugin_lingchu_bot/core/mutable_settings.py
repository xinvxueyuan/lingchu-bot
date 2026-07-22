"""Typed localstore repository for online-editable Lingchu settings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from _lingchu_bot_contracts import MutableRuntimeSettings
from nonebot import require
from pydantic import ValidationError

require("nonebot_plugin_localstore")
from nonebot_plugin_localstore import get_plugin_config_file

from ..database.toml_store import (
    DatabaseError,
    load_toml_dict_async,
    load_toml_dict_sync,
    write_toml_dict_file_async,
)

if TYPE_CHECKING:
    from pathlib import Path

MUTABLE_SETTINGS_FILENAME: Final = "runtime-overrides.toml"


class MutableSettingsError(RuntimeError):
    """The mutable settings file cannot be read or validated."""


class _SettingsCache:
    value: MutableRuntimeSettings | None = None


_cache = _SettingsCache()


def get_mutable_settings_file() -> Path:
    """Return the localstore-owned mutable settings file."""
    return get_plugin_config_file(MUTABLE_SETTINGS_FILENAME)


def _validate(raw: dict[str, object]) -> MutableRuntimeSettings:
    try:
        return MutableRuntimeSettings.model_validate(raw)
    except ValidationError as exc:
        raise MutableSettingsError(str(exc)) from exc


def load_mutable_settings_sync() -> MutableRuntimeSettings:
    """Read and cache mutable settings for synchronous runtime consumers."""
    try:
        raw = load_toml_dict_sync(
            get_mutable_settings_file(),
            default={},
            merge_default=False,
        )
    except DatabaseError as exc:
        raise MutableSettingsError(str(exc)) from exc
    _cache.value = _validate(raw)
    return _cache.value


def get_mutable_settings() -> MutableRuntimeSettings:
    """Return cached settings, loading them on first access."""
    if _cache.value is not None:
        return _cache.value
    return load_mutable_settings_sync()


async def load_mutable_settings() -> MutableRuntimeSettings:
    """Read and cache current mutable settings without blocking the event loop."""
    try:
        raw = await load_toml_dict_async(
            get_mutable_settings_file(),
            default={},
            merge_default=False,
        )
    except DatabaseError as exc:
        raise MutableSettingsError(str(exc)) from exc
    _cache.value = _validate(raw)
    return _cache.value


async def save_mutable_settings(settings: MutableRuntimeSettings) -> None:
    """Atomically replace the mutable settings file and refresh the cache."""
    try:
        await write_toml_dict_file_async(
            get_mutable_settings_file(),
            settings.model_dump(mode="json"),
        )
    except DatabaseError as exc:
        raise MutableSettingsError(str(exc)) from exc
    _cache.value = settings
