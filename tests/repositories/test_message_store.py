from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.repositories import message_store


@pytest.fixture
def fake_record() -> SimpleNamespace:
    return SimpleNamespace(id=1, message_id="msg-1", created_at=datetime.now(UTC))


async def test_record_event_received_creates_without_message_id(
    monkeypatch: pytest.MonkeyPatch,
    fake_record: SimpleNamespace,
) -> None:
    create = AsyncMock(return_value=fake_record)
    monkeypatch.setattr(message_store.orm_crud, "create", create)

    result = await message_store.record_event_received(
        platform="milky",
        adapter="Milky",
        bot_id="bot-1",
        conversation_id="group-1",
        user_id="user-1",
        message_id=None,
        event_type="message.group",
        message_type="group",
        text_summary="hello",
    )

    assert result is fake_record
    create.assert_awaited_once()


async def test_record_event_received_updates_duplicate_message(
    monkeypatch: pytest.MonkeyPatch,
    fake_record: SimpleNamespace,
) -> None:
    get_or_create = AsyncMock(return_value=(fake_record, False))
    update = AsyncMock(return_value=(1, True))
    get_one = AsyncMock(return_value=fake_record)
    monkeypatch.setattr(message_store.orm_crud, "get_or_create", get_or_create)
    monkeypatch.setattr(message_store.orm_crud, "update", update)
    monkeypatch.setattr(message_store.orm_crud, "get_one", get_one)

    result = await message_store.record_event_received(
        platform="milky",
        adapter="Milky",
        bot_id="bot-1",
        conversation_id="group-1",
        user_id="user-1",
        message_id="msg-1",
        event_type="message.group",
        message_type="group",
        text_summary="hello",
    )

    assert result is fake_record
    get_or_create.assert_awaited_once()
    update.assert_awaited_once()
    get_one.assert_awaited_once()


async def test_record_matcher_result_skips_missing_message_id() -> None:
    result = await message_store.record_matcher_result(
        platform="milky",
        bot_id="bot-1",
        conversation_id="group-1",
        message_id=None,
        process_status="handled",
    )

    assert result is False


async def test_list_recent_messages_filters_common_dimensions(
    monkeypatch: pytest.MonkeyPatch,
    fake_record: SimpleNamespace,
) -> None:
    list_items = AsyncMock(return_value=[fake_record])
    monkeypatch.setattr(message_store.orm_crud, "list_items", list_items)

    result = await message_store.list_recent_messages(
        conversation_id="group-1",
        user_id="user-1",
        limit=20,
    )

    assert result == [fake_record]
    list_items_args = list_items.await_args
    assert list_items_args is not None
    assert list_items_args.kwargs["filters"] == {
        "conversation_id": "group-1",
        "user_id": "user-1",
    }
    assert list_items_args.kwargs["order_by"] == ["-created_at"]


async def test_cleanup_expired_messages_uses_retention_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delete = AsyncMock(return_value=(3, True))
    monkeypatch.setattr(message_store.orm_crud, "delete", delete)

    result = await message_store.cleanup_expired_messages(retention_days=7)

    assert result == (3, True)
    delete.assert_awaited_once()
    delete_args = delete.await_args
    assert delete_args is not None
    assert delete_args.kwargs["conditions"]
