from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from _lingchu_bot_contracts import MutableRuntimeSettings
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.core import (
    mutable_settings as settings_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.core.mutable_settings import (
    MutableSettingsError,
    get_mutable_settings,
    load_mutable_settings,
    load_mutable_settings_sync,
    save_mutable_settings,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.toml_store import DatabaseError


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    settings_module._cache.value = None


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

    write.assert_awaited_once_with(target, settings.model_dump(mode="json"))
    assert get_mutable_settings() is settings


def test_invalid_mutable_settings_are_domain_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        settings_module,
        "load_toml_dict_sync",
        MagicMock(return_value={"unknown": True}),
    )

    with pytest.raises(MutableSettingsError, match="Extra inputs are not permitted"):
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
        await save_mutable_settings(MutableRuntimeSettings())
