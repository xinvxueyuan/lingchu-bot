from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.permissions import config as perm_config
from src.plugins.nonebot_plugin_lingchu_bot.permissions.config import (
    PASSTHROUGH_KEY,
    PlatformPermissionMappingUpdate,
    get_platform_runtime_passthrough_config,
    update_platform_runtime_passthrough_config,
)


def _patch_toml_helpers(
    monkeypatch: pytest.MonkeyPatch,
    load_return: dict[str, Any] | Exception,
) -> tuple[AsyncMock, AsyncMock]:
    if isinstance(load_return, Exception):
        load_mock = AsyncMock(side_effect=load_return)
    else:
        load_mock = AsyncMock(return_value=load_return)
    write_mock = AsyncMock()
    monkeypatch.setattr(perm_config, "load_toml_dict_async", load_mock)
    monkeypatch.setattr(perm_config, "write_toml_dict_file_async", write_mock)
    return load_mock, write_mock


@pytest.mark.asyncio
async def test_get_returns_bool_when_stored_bool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_mock, write_mock = _patch_toml_helpers(monkeypatch, {PASSTHROUGH_KEY: False})

    result = await get_platform_runtime_passthrough_config()

    assert result is False
    load_mock.assert_awaited_once()
    write_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_returns_normalized_dict_when_stored_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_mock, write_mock = _patch_toml_helpers(
        monkeypatch, {PASSTHROUGH_KEY: {"qq": 1, "telegram": 0}}
    )

    result = await get_platform_runtime_passthrough_config()

    assert result == {"qq": True, "telegram": False}
    load_mock.assert_awaited_once()
    write_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_returns_true_when_stored_unexpected_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_mock, write_mock = _patch_toml_helpers(
        monkeypatch, {PASSTHROUGH_KEY: [1, 2, 3]}
    )

    result = await get_platform_runtime_passthrough_config()

    assert result is True
    load_mock.assert_awaited_once()
    write_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_returns_true_when_db_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.plugins.nonebot_plugin_lingchu_bot.database.toml_store import DatabaseError

    load_mock, write_mock = _patch_toml_helpers(monkeypatch, DatabaseError("test"))

    result = await get_platform_runtime_passthrough_config()

    assert result is True
    load_mock.assert_awaited_once()
    write_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_sets_global_bool_when_platform_id_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_mock, write_mock = _patch_toml_helpers(monkeypatch, {})

    request = PlatformPermissionMappingUpdate(platform_id=None, enabled=False)

    result = await update_platform_runtime_passthrough_config(request)

    assert result is False
    load_mock.assert_awaited_once()
    write_mock.assert_awaited_once()
    written_data = write_mock.call_args.args[1]
    assert written_data[PASSTHROUGH_KEY] is False


@pytest.mark.asyncio
async def test_update_merges_when_platform_id_str_and_current_dict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_mock, write_mock = _patch_toml_helpers(
        monkeypatch, {PASSTHROUGH_KEY: {"qq": 1, "telegram": 0}}
    )

    request = PlatformPermissionMappingUpdate(platform_id="discord", enabled=True)

    result = await update_platform_runtime_passthrough_config(request)

    assert result == {"qq": True, "telegram": False, "discord": True}
    load_mock.assert_awaited_once()
    write_mock.assert_awaited_once()
    written_data = write_mock.call_args.args[1]
    assert written_data[PASSTHROUGH_KEY] == {
        "qq": 1,
        "telegram": 0,
        "discord": True,
    }


@pytest.mark.asyncio
async def test_update_converts_to_dict_when_platform_id_str_and_current_bool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_mock, write_mock = _patch_toml_helpers(monkeypatch, {PASSTHROUGH_KEY: True})

    request = PlatformPermissionMappingUpdate(platform_id="qq", enabled=False)

    result = await update_platform_runtime_passthrough_config(request)

    assert result == {"qq": False}
    load_mock.assert_awaited_once()
    write_mock.assert_awaited_once()
    written_data = write_mock.call_args.args[1]
    assert written_data[PASSTHROUGH_KEY] == {"qq": False}


def test_platform_permission_mapping_update_holds_fields() -> None:
    request = PlatformPermissionMappingUpdate(platform_id="qq", enabled=True)

    assert request.platform_id == "qq"
    assert request.enabled is True
