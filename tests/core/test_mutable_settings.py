import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from _lingchu_bot_contracts import MutableRuntimeSettings
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import (
    mutable_settings as settings_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.mutable_settings import (
    MutableSettingsError,
    flush_mutable_settings_if_dirty,
    get_mutable_settings,
    load_mutable_settings,
    load_mutable_settings_sync,
    reload_mutable_settings_from_disk,
    reset_mutable_settings_cache,
    save_mutable_settings,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.toml_store import DatabaseError


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    settings_module._cache.value = None
    settings_module._cache.dirty = False
    settings_module._cache.persisted_checksum = None


def test_load_mutable_settings_sync_validates_and_caches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    load = MagicMock(return_value={"permission_platform_runtime_passthrough": False})
    monkeypatch.setattr(
        settings_module,
        "get_mutable_settings_file",
        lambda: tmp_path / "runtime-overrides.toml",
    )
    monkeypatch.setattr(settings_module, "load_toml_dict_sync", load)

    result = load_mutable_settings_sync()

    assert result.permission_platform_runtime_passthrough is False
    assert get_mutable_settings() is result
    load.assert_called_once_with(
        tmp_path / "runtime-overrides.toml", default={}, merge_default=False
    )


def test_load_mutable_settings_sync_maps_storage_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings_module,
        "load_toml_dict_sync",
        MagicMock(side_effect=DatabaseError("broken")),
    )

    with pytest.raises(MutableSettingsError, match="broken"):
        load_mutable_settings_sync()


@pytest.mark.asyncio
async def test_load_mutable_settings_validates_async_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings_module,
        "load_toml_dict_async",
        AsyncMock(
            return_value={"command_trigger_overrides": {"menu": {"english": "help"}}}
        ),
    )

    result = await load_mutable_settings()

    assert result.command_trigger_overrides["menu"]["english"] == "help"
    assert settings_module._cache.value is result


@pytest.mark.asyncio
async def test_save_mutable_settings_serializes_and_refreshes_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "runtime-overrides.toml"
    write = AsyncMock()
    monkeypatch.setattr(settings_module, "get_mutable_settings_file", lambda: target)
    monkeypatch.setattr(settings_module, "write_toml_dict_file_async", write)
    settings = MutableRuntimeSettings(
        permission_platform_runtime_passthrough={"qq": False}
    )

    await save_mutable_settings(settings)

    write.assert_not_awaited()
    assert get_mutable_settings() is settings
    assert settings_module._cache.dirty is True


@pytest.mark.asyncio
async def test_flush_mutable_settings_if_dirty_writes_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "runtime-overrides.toml"
    write = AsyncMock()
    monkeypatch.setattr(settings_module, "get_mutable_settings_file", lambda: target)
    monkeypatch.setattr(settings_module, "write_toml_dict_file_async", write)
    settings = MutableRuntimeSettings(
        permission_platform_runtime_passthrough={"qq": False}
    )
    await save_mutable_settings(settings)

    first = await flush_mutable_settings_if_dirty()
    second = await flush_mutable_settings_if_dirty()

    assert first is True
    assert second is False
    write.assert_awaited_once_with(target, settings.to_dict())


def test_invalid_mutable_settings_are_domain_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings_module,
        "load_toml_dict_sync",
        MagicMock(return_value={"unknown": True}),
    )

    with pytest.raises(MutableSettingsError, match="unknown configuration fields"):
        load_mutable_settings_sync()


@pytest.mark.asyncio
async def test_load_mutable_settings_maps_async_storage_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings_module,
        "load_toml_dict_async",
        AsyncMock(side_effect=DatabaseError("async broken")),
    )

    with pytest.raises(MutableSettingsError, match="async broken"):
        await load_mutable_settings()
    assert settings_module._cache.value == MutableRuntimeSettings()
    assert settings_module._cache.dirty is False


@pytest.mark.asyncio
async def test_load_mutable_settings_resets_cache_on_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_module._cache.value = MutableRuntimeSettings(
        permission_platform_runtime_passthrough=False,
    )
    settings_module._cache.dirty = True
    monkeypatch.setattr(
        settings_module,
        "load_toml_dict_async",
        AsyncMock(return_value={"unknown": True}),
    )

    with pytest.raises(MutableSettingsError, match="unknown configuration fields"):
        await load_mutable_settings()

    assert settings_module._cache.value == MutableRuntimeSettings()
    assert settings_module._cache.dirty is False


@pytest.mark.asyncio
async def test_save_mutable_settings_maps_storage_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings_module,
        "write_toml_dict_file_async",
        AsyncMock(side_effect=DatabaseError("write broken")),
    )

    with pytest.raises(MutableSettingsError, match="write broken"):
        await save_mutable_settings(MutableRuntimeSettings(), flush=True)


@pytest.mark.asyncio
async def test_reload_mutable_settings_from_disk_delegates_to_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = MutableRuntimeSettings(
        command_trigger_overrides={"menu": {"english": "help"}}
    )
    loader = AsyncMock(return_value=expected)
    monkeypatch.setattr(settings_module, "load_mutable_settings", loader)

    result = await reload_mutable_settings_from_disk()

    loader.assert_awaited_once()
    assert result is expected


@pytest.mark.asyncio
async def test_flush_mutable_settings_retries_when_settings_change_during_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "runtime-overrides.toml"
    initial = MutableRuntimeSettings(
        permission_platform_runtime_passthrough=False,
    )
    updated = MutableRuntimeSettings(
        permission_platform_runtime_passthrough={"qq": False},
    )
    writes: list[dict[str, object]] = []

    async def write_settings(_path: Path, settings: dict[str, object]) -> None:
        writes.append(settings)
        if len(writes) == 1:
            await save_mutable_settings(updated)
            await asyncio.sleep(0)

    monkeypatch.setattr(settings_module, "get_mutable_settings_file", lambda: target)
    monkeypatch.setattr(settings_module, "write_toml_dict_file_async", write_settings)
    await save_mutable_settings(initial)

    assert await flush_mutable_settings_if_dirty() is True
    assert [write["permission_platform_runtime_passthrough"] for write in writes] == [
        False,
        {"qq": False},
    ]
    assert settings_module._cache.dirty is False


@pytest.mark.asyncio
async def test_flush_mutable_settings_stops_after_retries_are_exhausted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "runtime-overrides.toml"
    writes = 0

    async def write_settings(_path: Path, _settings: dict[str, object]) -> None:
        nonlocal writes
        writes += 1
        await save_mutable_settings(
            MutableRuntimeSettings(
                permission_platform_runtime_passthrough={"qq": writes % 2 == 1},
            )
        )

    monkeypatch.setattr(settings_module, "get_mutable_settings_file", lambda: target)
    monkeypatch.setattr(settings_module, "write_toml_dict_file_async", write_settings)
    await save_mutable_settings(
        MutableRuntimeSettings(permission_platform_runtime_passthrough=False)
    )

    assert await flush_mutable_settings_if_dirty() is True
    assert writes == 3
    assert settings_module._cache.dirty is True


def test_reset_mutable_settings_cache_uses_clean_defaults() -> None:
    settings_module._cache.value = MutableRuntimeSettings(
        permission_platform_runtime_passthrough=False,
    )
    settings_module._cache.dirty = True

    result = reset_mutable_settings_cache()

    assert result == MutableRuntimeSettings()
    assert settings_module._cache.value == MutableRuntimeSettings()
    assert settings_module._cache.dirty is False
