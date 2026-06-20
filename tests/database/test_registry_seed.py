"""Tests for registry seeding repository."""

from __future__ import annotations

from typing import Any
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


def _find_upsert_call_for_model(call_args_list: list, model: type) -> Any:
    """Return the first upsert call targeting ``model`` (order-independent)."""
    for call in call_args_list:
        if call.args[0] is model:
            return call
    pytest.fail(f"No upsert call found for {model.__name__}")


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
    # Order-independent: every model type must have been upserted.
    called_models = {call.args[0] for call in upsert_mock.call_args_list}
    assert called_models == {Platform, Adapter, ProtocolImplementation}


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

    platform_call = _find_upsert_call_for_model(upsert_mock.call_args_list, Platform)
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

    adapter_call = _find_upsert_call_for_model(upsert_mock.call_args_list, Adapter)
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

    protocol_call = _find_upsert_call_for_model(
        upsert_mock.call_args_list, ProtocolImplementation
    )
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
    """One failing entry must not abort the rest of the batch (order-independent)."""
    platform_error = DatabaseError("platform boom")

    def _raise_on_platform(model: type, *_args: object, **_kwargs: object) -> None:
        if model is Platform:
            raise platform_error

    upsert_mock = AsyncMock(side_effect=_raise_on_platform)

    with (
        patch.object(registry_repo, "upsert", upsert_mock),
        patch.object(
            registry_repo, "export_registry_for_seeding", return_value=_seed_data()
        ),
    ):
        await registry_repo.seed_registry_tables()

    assert upsert_mock.call_count == UPSERT_CALL_COUNT
    # Adapter and protocol were still upserted despite the platform failure.
    called_models = {call.args[0] for call in upsert_mock.call_args_list}
    assert Adapter in called_models
    assert ProtocolImplementation in called_models
    assert Platform in called_models


@pytest.mark.asyncio
async def test_seed_registry_tables_continues_after_one_item_fails_in_batch() -> None:
    """Within a single category, one failure must not abort the remaining items."""

    seed_data = _seed_data()
    seed_data["platforms"] = [
        {
            "platform_id": "qq",
            "display_name": "QQ",
            "capabilities": "[]",
            "implemented": True,
        },
        {
            "platform_id": "discord",
            "display_name": "Discord",
            "capabilities": "[]",
            "implemented": True,
        },
        {
            "platform_id": "telegram",
            "display_name": "Telegram",
            "capabilities": "[]",
            "implemented": True,
        },
    ]

    telegram_error = DatabaseError("telegram boom")

    def _raise_on_telegram(
        model: type, insert_values: dict[str, Any], **_kwargs: object
    ) -> None:
        if model is Platform and insert_values.get("platform_id") == "telegram":
            raise telegram_error

    upsert_mock = AsyncMock(side_effect=_raise_on_telegram)

    with (
        patch.object(registry_repo, "upsert", upsert_mock),
        patch.object(
            registry_repo, "export_registry_for_seeding", return_value=seed_data
        ),
    ):
        await registry_repo.seed_registry_tables()

    # All items attempted: 3 platforms + 1 adapter + 1 protocol.
    expected_count = (
        len(seed_data["platforms"])
        + len(seed_data["adapters"])
        + len(seed_data["protocol_implementations"])
    )
    assert upsert_mock.call_count == expected_count
    platform_ids = [
        call.args[1].get("platform_id")
        for call in upsert_mock.call_args_list
        if call.args[0] is Platform
    ]
    assert set(platform_ids) == {"qq", "discord", "telegram"}
