from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.permissions import config as perm_config
from src.plugins.nonebot_plugin_lingchu_bot.permissions.config import (
    PASSTHROUGH_KEY,
    PlatformPermissionMappingUpdate,
    get_platform_runtime_passthrough_config,
    update_platform_runtime_passthrough_config,
)


def _patch_toml_db(
    monkeypatch: pytest.MonkeyPatch,
    read_return: Any,
) -> MagicMock:
    """Patch RobustAsyncTOMLDB with a fake async DB and return the fake db."""
    fake_db = MagicMock()
    fake_db.__aenter__.return_value = fake_db
    fake_db.read = AsyncMock(return_value=read_return)
    fake_db.set = AsyncMock()
    monkeypatch.setattr(
        perm_config, "RobustAsyncTOMLDB", MagicMock(return_value=fake_db)
    )
    return fake_db


@pytest.mark.asyncio
async def test_get_returns_bool_when_stored_bool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_db = _patch_toml_db(monkeypatch, read_return=False)

    result = await get_platform_runtime_passthrough_config()

    assert result is False
    fake_db.read.assert_awaited_once_with(PASSTHROUGH_KEY, default=True)
    fake_db.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_returns_normalized_dict_when_stored_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_db = _patch_toml_db(monkeypatch, read_return={"qq": 1, "telegram": 0})

    result = await get_platform_runtime_passthrough_config()

    assert result == {"qq": True, "telegram": False}
    fake_db.read.assert_awaited_once_with(PASSTHROUGH_KEY, default=True)
    fake_db.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_returns_true_when_stored_unexpected_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_db = _patch_toml_db(monkeypatch, read_return=[1, 2, 3])

    result = await get_platform_runtime_passthrough_config()

    assert result is True
    fake_db.read.assert_awaited_once_with(PASSTHROUGH_KEY, default=True)
    fake_db.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_sets_global_bool_when_platform_id_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_db = _patch_toml_db(monkeypatch, read_return=None)

    request = PlatformPermissionMappingUpdate(platform_id=None, enabled=False)

    result = await update_platform_runtime_passthrough_config(request)

    assert result is False
    fake_db.read.assert_not_awaited()
    fake_db.set.assert_awaited_once_with(PASSTHROUGH_KEY, request.enabled)


@pytest.mark.asyncio
async def test_update_merges_when_platform_id_str_and_current_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_db = _patch_toml_db(monkeypatch, read_return={"qq": 1, "telegram": 0})

    request = PlatformPermissionMappingUpdate(platform_id="discord", enabled=True)

    result = await update_platform_runtime_passthrough_config(request)

    assert result == {"qq": True, "telegram": False, "discord": True}
    fake_db.read.assert_awaited_once_with(PASSTHROUGH_KEY, {})
    fake_db.set.assert_awaited_once_with(
        PASSTHROUGH_KEY, {"qq": 1, "telegram": 0, "discord": True}
    )


@pytest.mark.asyncio
async def test_update_converts_to_dict_when_platform_id_str_and_current_bool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_db = _patch_toml_db(monkeypatch, read_return=True)

    request = PlatformPermissionMappingUpdate(platform_id="qq", enabled=False)

    result = await update_platform_runtime_passthrough_config(request)

    assert result == {"qq": False}
    fake_db.read.assert_awaited_once_with(PASSTHROUGH_KEY, {})
    fake_db.set.assert_awaited_once_with(PASSTHROUGH_KEY, {"qq": request.enabled})


def test_platform_permission_mapping_update_holds_fields() -> None:
    request = PlatformPermissionMappingUpdate(platform_id="qq", enabled=True)

    assert request.platform_id == "qq"
    assert request.enabled is True
