from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.models import BlocklistEntry
from src.plugins.nonebot_plugin_lingchu_bot.repositories import blocklist

GET_ONE_GROUP_LOOKUP_COUNT = 2


def _entry(*, expires_at: datetime | None = None) -> MagicMock:
    item = MagicMock(spec=BlocklistEntry)
    item.expires_at = expires_at
    item.reason = "blocked"
    return item


def test_scope_key_for_group_and_global() -> None:
    assert blocklist.scope_key_for("group", 123) == "123"
    assert blocklist.scope_key_for("global", 123) == "*"
    with pytest.raises(ValueError, match="group_id"):
        blocklist.scope_key_for("group", None)


def test_expires_at_from_duration_defaults_to_permanent() -> None:
    assert blocklist.expires_at_from_duration(None) is None
    assert blocklist.expires_at_from_duration(0) is None
    assert blocklist.expires_at_from_duration(-1) is None
    assert blocklist.expires_at_from_duration(60) is not None


@pytest.mark.asyncio
async def test_upsert_block_uses_scope_identity_and_update_values() -> None:
    upsert_mock = AsyncMock(return_value=_entry())

    with patch.object(blocklist, "upsert", upsert_mock):
        await blocklist.upsert_block(
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            scope="group",
            group_id=123,
            user_id=456,
            operator_id=789,
            reason="bad",
            expires_at=None,
        )

    _, insert_values = upsert_mock.call_args.args[:2]
    assert insert_values["scope"] == "group"
    assert insert_values["scope_key"] == "123"
    assert insert_values["group_id"] == "123"
    assert insert_values["user_id"] == "456"
    assert upsert_mock.call_args.kwargs["conflict_fields"] == [
        "platform_id",
        "adapter_id",
        "bot_id",
        "scope",
        "scope_key",
        "user_id",
    ]
    assert upsert_mock.call_args.kwargs["update_values"]["reason"] == "bad"


@pytest.mark.asyncio
async def test_remove_and_clear_use_expected_scope_filters() -> None:
    delete_mock = AsyncMock(return_value=(1, True))

    with patch.object(blocklist, "delete", delete_mock):
        await blocklist.remove_block(
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            scope="global",
            group_id=123,
            user_id=456,
        )
        await blocklist.clear_blocklist(
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            scope="group",
            group_id=123,
        )

    first_filters = delete_mock.call_args_list[0].args[1]
    second_filters = delete_mock.call_args_list[1].args[1]
    assert first_filters["scope"] == "global"
    assert first_filters["scope_key"] == "*"
    assert first_filters["user_id"] == "456"
    assert second_filters["scope"] == "group"
    assert second_filters["scope_key"] == "123"
    assert "user_id" not in second_filters


@pytest.mark.asyncio
async def test_find_active_block_prefers_global_entry() -> None:
    get_one_mock = AsyncMock(return_value=_entry())

    with patch.object(blocklist, "get_one", get_one_mock):
        result = await blocklist.find_active_block(
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            group_id=123,
            user_id=456,
        )

    assert result is not None
    assert get_one_mock.await_count == 1
    assert get_one_mock.call_args.args[1]["scope"] == "global"


@pytest.mark.asyncio
async def test_find_active_block_falls_back_to_group_entry() -> None:
    get_one_mock = AsyncMock(side_effect=[None, _entry()])

    with patch.object(blocklist, "get_one", get_one_mock):
        result = await blocklist.find_active_block(
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            group_id=123,
            user_id=456,
        )

    assert result is not None
    assert get_one_mock.await_count == GET_ONE_GROUP_LOOKUP_COUNT
    assert get_one_mock.call_args_list[1].args[1]["scope"] == "group"


@pytest.mark.asyncio
async def test_find_active_block_lazily_deletes_expired_entries() -> None:
    expired = _entry(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    get_one_mock = AsyncMock(side_effect=[expired, None])
    delete_mock = AsyncMock(return_value=(1, True))

    with (
        patch.object(blocklist, "get_one", get_one_mock),
        patch.object(blocklist, "delete", delete_mock),
    ):
        result = await blocklist.find_active_block(
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            group_id=123,
            user_id=456,
        )

    assert result is None
    delete_mock.assert_awaited_once()
