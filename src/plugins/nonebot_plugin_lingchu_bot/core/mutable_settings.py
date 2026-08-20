"""Typed localstore repository for online-editable Lingchu settings."""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import TYPE_CHECKING, Final

from _lingchu_bot_contracts import MutableRuntimeSettings
from nonebot import require

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
    dirty: bool = False
    persisted_checksum: str | None = None


_cache = _SettingsCache()
_flush_lock = asyncio.Lock()


def get_mutable_settings_file() -> Path:
    """Return the localstore-owned mutable settings file."""
    return get_plugin_config_file(MUTABLE_SETTINGS_FILENAME)


def _validate(raw: dict[str, object]) -> MutableRuntimeSettings:
    try:
        return MutableRuntimeSettings.from_mapping(raw)
    except ValueError as exc:
        raise MutableSettingsError(str(exc)) from exc


def _checksum(settings: MutableRuntimeSettings) -> str:
    payload = json.dumps(
        settings.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _set_loaded_cache(settings: MutableRuntimeSettings) -> None:
    _cache.value = settings
    _cache.persisted_checksum = _checksum(settings)
    _cache.dirty = False


def reset_mutable_settings_cache() -> MutableRuntimeSettings:
    """Replace the cache with clean defaults without writing to disk."""
    settings = MutableRuntimeSettings()
    _set_loaded_cache(settings)
    return settings


def load_mutable_settings_sync() -> MutableRuntimeSettings:
    """Read and cache mutable settings for synchronous runtime consumers."""
    try:
        raw = load_toml_dict_sync(
            get_mutable_settings_file(),
            default={},
            merge_default=False,
        )
        settings = _validate(raw)
    except DatabaseError as exc:
        reset_mutable_settings_cache()
        raise MutableSettingsError(str(exc)) from exc
    except MutableSettingsError:
        reset_mutable_settings_cache()
        raise
    _set_loaded_cache(settings)
    return settings


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
        settings = _validate(raw)
    except DatabaseError as exc:
        reset_mutable_settings_cache()
        raise MutableSettingsError(str(exc)) from exc
    except MutableSettingsError:
        reset_mutable_settings_cache()
        raise
    _set_loaded_cache(settings)
    return settings


async def save_mutable_settings(
    settings: MutableRuntimeSettings,
    *,
    flush: bool = False,
) -> None:
    """Update in-memory mutable settings and optionally flush to disk."""
    checksum = _checksum(settings)
    _cache.value = settings
    _cache.dirty = checksum != _cache.persisted_checksum
    if flush:
        await flush_mutable_settings_if_dirty()


async def flush_mutable_settings_if_dirty() -> bool:
    """Persist settings with a stable snapshot and post-write validation."""
    async with _flush_lock:
        flushed = False
        while True:
            settings = _cache.value
            if settings is None:
                return flushed
            snapshot = MutableRuntimeSettings.from_mapping(settings.to_dict())
            snapshot_checksum = _checksum(snapshot)
            if not _cache.dirty or snapshot_checksum == _cache.persisted_checksum:
                _cache.dirty = False
                return flushed
            try:
                await write_toml_dict_file_async(
                    get_mutable_settings_file(),
                    snapshot.to_dict(),
                )
            except DatabaseError as exc:
                raise MutableSettingsError(str(exc)) from exc
            _cache.persisted_checksum = snapshot_checksum
            flushed = True

            current = _cache.value
            if current is not None and _checksum(current) == snapshot_checksum:
                _cache.dirty = False
                return True
            _cache.dirty = True


async def reload_mutable_settings_from_disk() -> MutableRuntimeSettings:
    """Reload mutable settings from disk and replace in-memory cache."""
    return await load_mutable_settings()
