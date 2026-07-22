from unittest.mock import AsyncMock

from _lingchu_bot_contracts import MutableRuntimeSettings
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.permissions import config as config_module
from src.plugins.nonebot_plugin_lingchu_bot.permissions.config import (
    PlatformPermissionMappingUpdate,
    get_platform_runtime_passthrough_config,
    update_platform_runtime_passthrough_config,
)


@pytest.mark.asyncio
async def test_get_platform_runtime_passthrough_uses_typed_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load = AsyncMock(
        return_value=MutableRuntimeSettings(
            permission_platform_runtime_passthrough={"qq": False}
        )
    )
    monkeypatch.setattr(config_module, "load_mutable_settings", load)

    assert await get_platform_runtime_passthrough_config() == {"qq": False}
    load.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_platform_runtime_passthrough_preserves_other_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = MutableRuntimeSettings(
        command_trigger_overrides={"menu": {"en": "menu"}}
    )
    monkeypatch.setattr(
        config_module, "load_mutable_settings", AsyncMock(return_value=original)
    )
    save = AsyncMock()
    monkeypatch.setattr(config_module, "save_mutable_settings", save)

    result = await update_platform_runtime_passthrough_config(
        PlatformPermissionMappingUpdate(platform_id="qq", enabled=False)
    )

    assert result == {"qq": False}
    assert save.await_args is not None
    saved = save.await_args.args[0]
    assert isinstance(saved, MutableRuntimeSettings)
    assert saved.permission_platform_runtime_passthrough == {"qq": False}
    assert saved.command_trigger_overrides == original.command_trigger_overrides


@pytest.mark.asyncio
async def test_update_global_platform_runtime_passthrough(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        config_module,
        "load_mutable_settings",
        AsyncMock(return_value=MutableRuntimeSettings()),
    )
    save = AsyncMock()
    monkeypatch.setattr(config_module, "save_mutable_settings", save)

    result = await update_platform_runtime_passthrough_config(
        PlatformPermissionMappingUpdate(platform_id=None, enabled=False)
    )

    assert result is False
    assert save.await_args is not None
    assert save.await_args.args[0].permission_platform_runtime_passthrough is False


@pytest.mark.asyncio
async def test_get_platform_runtime_passthrough_uses_default_on_read_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        config_module,
        "load_mutable_settings",
        AsyncMock(side_effect=config_module.MutableSettingsError("broken")),
    )

    assert await get_platform_runtime_passthrough_config() is True


@pytest.mark.asyncio
async def test_update_uses_defaults_and_suppresses_write_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        config_module,
        "load_mutable_settings",
        AsyncMock(side_effect=config_module.MutableSettingsError("broken")),
    )
    monkeypatch.setattr(
        config_module,
        "save_mutable_settings",
        AsyncMock(side_effect=config_module.MutableSettingsError("write broken")),
    )

    result = await update_platform_runtime_passthrough_config(
        PlatformPermissionMappingUpdate(platform_id="qq", enabled=False)
    )

    assert result == {"qq": False}
