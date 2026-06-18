"""Tests for registry seeding repository."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.models import (
    Adapter,
    Platform,
    ProtocolImplementation,
)
from src.plugins.nonebot_plugin_lingchu_bot.database.orm_crud import DatabaseError
from src.plugins.nonebot_plugin_lingchu_bot.repositories import (
    registry as registry_repo,
)

UPSERT_CALL_COUNT = 3


def _seed_data() -> dict[str, list[dict[str, object]]]:
    return {
        "platforms": [
            {
                "platform_id": "qq",
                "display_name": "QQ",
                "capabilities": "[]",
                "implemented": True,
            },
        ],
        "adapters": [
            {
                "adapter_id": "~onebot.v11",
                "platform_id": "qq",
                "display_name": "onebot v11",
                "nonebot_adapter_id": "~onebot.v11",
            },
        ],
        "protocol_implementations": [
            {
                "protocol_id": "default",
                "adapter_id": "~onebot.v11",
                "display_name": "Default",
                "module_path": "handle.qq.adapters.onebot11.default",
            },
        ],
    }


@pytest.mark.asyncio
async def test_seed_registry_tables_calls_upsert_for_each_entry() -> None:
    upsert_mock = AsyncMock()

    with (
        patch.object(registry_repo, "upsert", upsert_mock),
        patch.object(
            registry_repo, "export_registry_for_seeding", return_value=_seed_data()
        ),
    ):
        await registry_repo.seed_registry_tables()

    assert upsert_mock.call_count == UPSERT_CALL_COUNT


@pytest.mark.asyncio
async def test_seed_registry_tables_upserts_platform_with_correct_args() -> None:
    upsert_mock = AsyncMock()

    with (
        patch.object(registry_repo, "upsert", upsert_mock),
        patch.object(
            registry_repo, "export_registry_for_seeding", return_value=_seed_data()
        ),
    ):
        await registry_repo.seed_registry_tables()

    platform_call = upsert_mock.call_args_list[0]
    assert platform_call.args[0] is Platform
    assert platform_call.args[1] == {
        "platform_id": "qq",
        "display_name": "QQ",
        "capabilities": "[]",
        "implemented": True,
    }
    assert platform_call.kwargs["conflict_fields"] == ["platform_id"]


@pytest.mark.asyncio
async def test_seed_registry_tables_upserts_adapter_with_correct_args() -> None:
    upsert_mock = AsyncMock()

    with (
        patch.object(registry_repo, "upsert", upsert_mock),
        patch.object(
            registry_repo, "export_registry_for_seeding", return_value=_seed_data()
        ),
    ):
        await registry_repo.seed_registry_tables()

    adapter_call = upsert_mock.call_args_list[1]
    assert adapter_call.args[0] is Adapter
    assert adapter_call.args[1] == {
        "adapter_id": "~onebot.v11",
        "platform_id": "qq",
        "display_name": "onebot v11",
        "nonebot_adapter_id": "~onebot.v11",
    }
    assert adapter_call.kwargs["conflict_fields"] == ["adapter_id"]


@pytest.mark.asyncio
async def test_seed_registry_tables_upserts_protocol_with_correct_args() -> None:
    upsert_mock = AsyncMock()

    with (
        patch.object(registry_repo, "upsert", upsert_mock),
        patch.object(
            registry_repo, "export_registry_for_seeding", return_value=_seed_data()
        ),
    ):
        await registry_repo.seed_registry_tables()

    protocol_call = upsert_mock.call_args_list[2]
    assert protocol_call.args[0] is ProtocolImplementation
    assert protocol_call.args[1] == {
        "protocol_id": "default",
        "adapter_id": "~onebot.v11",
        "display_name": "Default",
        "module_path": "handle.qq.adapters.onebot11.default",
    }
    assert protocol_call.kwargs["conflict_fields"] == ["adapter_id", "protocol_id"]


@pytest.mark.asyncio
async def test_seed_registry_tables_swallows_database_errors() -> None:
    upsert_mock = AsyncMock(side_effect=DatabaseError("boom"))

    with (
        patch.object(registry_repo, "upsert", upsert_mock),
        patch.object(
            registry_repo, "export_registry_for_seeding", return_value=_seed_data()
        ),
    ):
        await registry_repo.seed_registry_tables()

    assert upsert_mock.call_count == UPSERT_CALL_COUNT


@pytest.mark.asyncio
async def test_seed_registry_tables_continues_after_platform_error() -> None:
    upsert_mock = AsyncMock(
        side_effect=[DatabaseError("platform boom"), None, None],
    )

    with (
        patch.object(registry_repo, "upsert", upsert_mock),
        patch.object(
            registry_repo, "export_registry_for_seeding", return_value=_seed_data()
        ),
    ):
        await registry_repo.seed_registry_tables()

    assert upsert_mock.call_count == UPSERT_CALL_COUNT
    assert upsert_mock.call_args_list[1].args[0] is Adapter
    assert upsert_mock.call_args_list[2].args[0] is ProtocolImplementation
