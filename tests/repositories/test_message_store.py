from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.models import (
    AuditRecord,
    MessageRecord,
    QQOneBotV11NoneBotAuditRecord,
    QQOneBotV11NoneBotEventRecord,
)
from src.plugins.nonebot_plugin_lingchu_bot.repositories import message_store

LIST_ITEMS_LIMIT = 10
DELETE_CALL_COUNT = 4


def _message_record(*, record_id: int = 1) -> MagicMock:
    item = MagicMock(spec=MessageRecord)
    item.id = record_id
    item.protocol_id = None
    return item


def _audit_record() -> MagicMock:
    return MagicMock(spec=AuditRecord)


@pytest.mark.asyncio
async def test_message_page_revalidates_anchor_after_cleanup_race() -> None:
    anchor = _message_record(record_id=50)
    page_record = _message_record(record_id=40)
    list_mock = AsyncMock(side_effect=[[anchor], [page_record], []])
    after = datetime(2026, 7, 18, 7, 5, tzinfo=UTC)

    with patch.object(message_store, "list_items", list_mock):
        records, anchor_exists = await message_store.list_conversation_message_page(
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id="napcat",
            framework_id="nonebot",
            bot_id="bot-1",
            conversation_type="group",
            conversation_id="group-1",
            limit=3,
            after_received_at=after,
            after_record_id="50",
            window_received_at=datetime(2026, 7, 18, 7, 10, tzinfo=UTC),
            window_record_id="80",
        )

    assert records == [page_record]
    assert anchor_exists is False
    assert list_mock.await_count == 3


@pytest.mark.asyncio
async def test_record_event_received_with_none_message_id_calls_create() -> None:
    record_mock = _message_record()
    create_mock = AsyncMock(return_value=record_mock)

    with patch.object(message_store, "create", create_mock):
        result = await message_store.record_event_received(
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id=None,
            bot_id="bot-1",
            conversation_id="group-1",
            user_id="user-1",
            message_id=None,
            event_type="message.group",
            message_type="group",
            text_summary="hello",
            raw_message='[{"type":"text","data":{"text":"hello"}}]',
            raw_event='{"post_type":"message","raw_key":1}',
        )

    assert result is record_mock
    create_mock.assert_awaited_once()
    assert create_mock.call_args.args[0] is QQOneBotV11NoneBotEventRecord
    kwargs = create_mock.call_args.kwargs
    assert kwargs["platform_id"] == "qq"
    assert kwargs["adapter_id"] == "~onebot.v11"
    assert kwargs["protocol_id"] is None
    assert kwargs["bot_id"] == "bot-1"
    assert kwargs["conversation_id"] == "group-1"
    assert kwargs["user_id"] == "user-1"
    assert kwargs["message_id"] is None
    assert kwargs["event_type"] == "message.group"
    assert kwargs["message_type"] == "group"
    assert kwargs["text_summary"] == "hello"
    assert kwargs["raw_message"] == '[{"type":"text","data":{"text":"hello"}}]'
    assert kwargs["raw_event"] == '{"post_type":"message","raw_key":1}'
    assert kwargs["process_status"] == "received"
    assert kwargs["exception_summary"] is None
    assert "created_at" in kwargs
    assert "updated_at" in kwargs


@pytest.mark.asyncio
async def test_record_event_received_with_message_id_calls_upsert() -> None:
    record_mock = _message_record()
    upsert_mock = AsyncMock(return_value=record_mock)

    with patch.object(message_store, "upsert", upsert_mock):
        result = await message_store.record_event_received(
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id=None,
            bot_id="bot-1",
            conversation_id="group-1",
            user_id="user-1",
            message_id="msg-1",
            event_type="message.group",
            message_type="group",
            text_summary="hello",
            raw_message='"hello"',
            raw_event='{"message_id":"msg-1"}',
        )

    assert result is record_mock
    upsert_mock.assert_awaited_once()
    assert upsert_mock.call_args.args[0] is QQOneBotV11NoneBotEventRecord
    insert_values = upsert_mock.call_args.args[1]
    assert insert_values["platform_id"] == "qq"
    assert insert_values["adapter_id"] == "~onebot.v11"
    assert insert_values["protocol_id"] is None
    assert insert_values["bot_id"] == "bot-1"
    assert insert_values["conversation_id"] == "group-1"
    assert insert_values["user_id"] == "user-1"
    assert insert_values["message_id"] == "msg-1"
    assert insert_values["event_type"] == "message.group"
    assert insert_values["event_category"] == "message"
    assert insert_values["framework_id"] == "nonebot"
    assert insert_values["message_type"] == "group"
    assert insert_values["text_summary"] == "hello"
    assert insert_values["raw_message"] == '"hello"'
    assert insert_values["raw_event"] == '{"message_id":"msg-1"}'
    assert insert_values["process_status"] == "received"
    assert insert_values["exception_summary"] is None
    assert "created_at" in insert_values
    assert "updated_at" in insert_values
    assert upsert_mock.call_args.kwargs["conflict_fields"] == [
        "platform_id",
        "adapter_id",
        "protocol_id",
        "bot_id",
        "conversation_id",
        "message_id",
    ]


@pytest.mark.asyncio
async def test_record_event_received_passes_protocol_id_through_to_create() -> None:
    record_mock = _message_record()
    create_mock = AsyncMock(return_value=record_mock)

    with patch.object(message_store, "create", create_mock):
        await message_store.record_event_received(
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id="napcat",
            bot_id="bot-1",
            conversation_id="group-1",
            user_id="user-1",
            message_id=None,
            event_type="message.group",
            message_type="group",
            text_summary="hello",
            raw_message='"hello"',
            raw_event='{"message_id":"msg-1"}',
        )

    create_mock.assert_awaited_once()
    assert create_mock.call_args.kwargs["protocol_id"] == "napcat"


@pytest.mark.asyncio
async def test_record_event_received_passes_protocol_id_through_to_upsert() -> None:
    record_mock = _message_record()
    upsert_mock = AsyncMock(return_value=record_mock)

    with patch.object(message_store, "upsert", upsert_mock):
        await message_store.record_event_received(
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id="napcat",
            bot_id="bot-1",
            conversation_id="group-1",
            user_id="user-1",
            message_id="msg-1",
            event_type="message.group",
            message_type="group",
            text_summary="hello",
            raw_message='"hello"',
            raw_event='{"message_id":"msg-1"}',
        )

    upsert_mock.assert_awaited_once()
    insert_values = upsert_mock.call_args.args[1]
    assert insert_values["protocol_id"] == "napcat"


@pytest.mark.asyncio
async def test_record_matcher_result_updates_record_when_found() -> None:
    record_mock = _message_record(record_id=42)
    get_one_mock = AsyncMock(return_value=record_mock)
    update_mock = AsyncMock()

    with (
        patch.object(message_store, "get_one", get_one_mock),
        patch.object(message_store, "update", update_mock),
    ):
        result = await message_store.record_matcher_result(
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id=None,
            bot_id="bot-1",
            conversation_id="group-1",
            message_id="msg-1",
            process_status="handled",
            exception_summary="boom",
        )

    assert result is True
    get_one_mock.assert_awaited_once()
    assert get_one_mock.call_args.args[0] is QQOneBotV11NoneBotEventRecord
    assert get_one_mock.call_args.args[1] == {
        "platform_id": "qq",
        "adapter_id": "~onebot.v11",
        "bot_id": "bot-1",
        "conversation_id": "group-1",
        "message_id": "msg-1",
    }
    update_mock.assert_awaited_once()
    assert update_mock.call_args.args[0] is QQOneBotV11NoneBotEventRecord
    assert update_mock.call_args.args[1] == {"id": 42}
    update_values = update_mock.call_args.args[2]
    assert update_values["process_status"] == "handled"
    assert update_values["exception_summary"] == "boom"
    assert "updated_at" in update_values


@pytest.mark.asyncio
async def test_record_matcher_result_filters_by_protocol_id() -> None:
    record_mock = _message_record(record_id=42)
    get_one_mock = AsyncMock(return_value=record_mock)
    update_mock = AsyncMock()

    with (
        patch.object(message_store, "get_one", get_one_mock),
        patch.object(message_store, "update", update_mock),
    ):
        result = await message_store.record_matcher_result(
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id="napcat",
            bot_id="bot-1",
            conversation_id="group-1",
            message_id="msg-1",
            process_status="handled",
        )

    assert result is True
    filters = get_one_mock.call_args.args[1]
    assert filters["protocol_id"] == "napcat"


@pytest.mark.asyncio
async def test_record_matcher_result_returns_false_when_message_id_none() -> None:
    get_one_mock = AsyncMock()
    update_mock = AsyncMock()

    with (
        patch.object(message_store, "get_one", get_one_mock),
        patch.object(message_store, "update", update_mock),
    ):
        result = await message_store.record_matcher_result(
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id=None,
            bot_id="bot-1",
            conversation_id="group-1",
            message_id=None,
            process_status="handled",
        )

    assert result is False
    get_one_mock.assert_not_awaited()
    update_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_matcher_result_returns_false_when_not_found() -> None:
    get_one_mock = AsyncMock(return_value=None)
    update_mock = AsyncMock()

    with (
        patch.object(message_store, "get_one", get_one_mock),
        patch.object(message_store, "update", update_mock),
    ):
        result = await message_store.record_matcher_result(
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id=None,
            bot_id="bot-1",
            conversation_id="group-1",
            message_id="msg-1",
            process_status="handled",
        )

    assert result is False
    get_one_mock.assert_awaited_once()
    update_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_record_api_call_accepts_structured_request() -> None:
    audit_mock = _audit_record()
    create_mock = AsyncMock(return_value=audit_mock)

    with patch.object(message_store, "create", create_mock):
        result = await message_store.record_api_call(
            message_store.AuditEvent(
                platform_id="qq",
                adapter_id="~onebot.v11",
                protocol_id=None,
                bot_id="bot-1",
                api_name="send_message",
                data_summary='{"message":"hello"}',
                result_summary='{"message_id":"out-1"}',
                exception_summary=None,
            )
        )

    assert result is audit_mock
    assert create_mock.call_args.kwargs["event_type"] == "send_message"
    assert create_mock.call_args.kwargs["audit_type"] == "api_call"


@pytest.mark.asyncio
async def test_record_api_call_calls_create_with_audit_record() -> None:
    audit_mock = _audit_record()
    create_mock = AsyncMock(return_value=audit_mock)

    with patch.object(message_store, "create", create_mock):
        result = await message_store.record_api_call(
            message_store.AuditEvent(
                platform_id="qq",
                adapter_id="~onebot.v11",
                protocol_id=None,
                bot_id="bot-1",
                api_name="send_message",
                data_summary='{"message":"hello"}',
                result_summary='{"message_id":"out-1"}',
                exception_summary=None,
            )
        )

    assert result is audit_mock
    create_mock.assert_awaited_once()
    assert create_mock.call_args.args[0] is QQOneBotV11NoneBotAuditRecord
    kwargs = create_mock.call_args.kwargs
    assert kwargs["platform_id"] == "qq"
    assert kwargs["adapter_id"] == "~onebot.v11"
    assert kwargs["protocol_id"] is None
    assert kwargs["bot_id"] == "bot-1"
    assert kwargs["audit_type"] == "api_call"
    assert kwargs["framework_id"] == "nonebot"
    assert kwargs["event_type"] == "send_message"
    assert kwargs["data_summary"] == '{"message":"hello"}'
    assert kwargs["result_summary"] == '{"message_id":"out-1"}'
    assert kwargs["exception_summary"] is None
    assert "created_at" in kwargs


@pytest.mark.asyncio
async def test_record_api_call_passes_protocol_id_through_to_create() -> None:
    audit_mock = _audit_record()
    create_mock = AsyncMock(return_value=audit_mock)

    with patch.object(message_store, "create", create_mock):
        await message_store.record_api_call(
            message_store.AuditEvent(
                platform_id="qq",
                adapter_id="~onebot.v11",
                protocol_id="napcat",
                bot_id="bot-1",
                api_name="send_message",
                data_summary='{"message":"hello"}',
                result_summary='{"message_id":"out-1"}',
                exception_summary=None,
            )
        )

    create_mock.assert_awaited_once()
    assert create_mock.call_args.kwargs["protocol_id"] == "napcat"


@pytest.mark.asyncio
async def test_list_recent_messages_calls_list_items_with_filters() -> None:
    records = [_message_record(record_id=1), _message_record(record_id=2)]
    list_items_mock = AsyncMock(return_value=records)

    with patch.object(message_store, "list_items", list_items_mock):
        result = await message_store.list_recent_messages(
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            conversation_id="group-1",
            user_id="user-1",
            limit=10,
        )

    assert result == records
    list_items_mock.assert_awaited_once()
    assert list_items_mock.call_args.args[0] is QQOneBotV11NoneBotEventRecord
    assert list_items_mock.call_args.args[1] == {
        "platform_id": "qq",
        "adapter_id": "~onebot.v11",
        "bot_id": "bot-1",
        "conversation_id": "group-1",
        "user_id": "user-1",
    }
    assert list_items_mock.call_args.kwargs["order_by"] == ["-created_at"]
    assert list_items_mock.call_args.kwargs["limit"] == LIST_ITEMS_LIMIT


@pytest.mark.asyncio
async def test_list_recent_messages_uses_platform_only_by_default() -> None:
    list_items_mock = AsyncMock(return_value=[])

    with patch.object(message_store, "list_items", list_items_mock):
        await message_store.list_recent_messages(platform_id="qq")

    assert list_items_mock.call_args.args[1] == {"platform_id": "qq"}


@pytest.mark.asyncio
async def test_list_recent_messages_includes_protocol_id_filter_when_provided() -> None:
    list_items_mock = AsyncMock(return_value=[])

    with patch.object(message_store, "list_items", list_items_mock):
        await message_store.list_recent_messages(
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id="napcat",
        )

    filters = list_items_mock.call_args.args[1]
    assert filters["protocol_id"] == "napcat"


@pytest.mark.asyncio
async def test_list_conversation_messages_applies_resource_before_pagination() -> None:
    list_items_mock = AsyncMock(return_value=[])

    with patch.object(message_store, "list_items", list_items_mock):
        await message_store.list_conversation_messages(
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id="napcat",
            framework_id="nonebot",
            bot_id="bot-1",
            conversation_type="group",
            conversation_id="group-1",
            limit=10,
        )

    list_items_mock.assert_awaited_once()
    assert list_items_mock.call_args.args[0] is QQOneBotV11NoneBotEventRecord
    assert list_items_mock.call_args.args[1] == {
        "platform_id": "qq",
        "adapter_id": "~onebot.v11",
        "protocol_id": "napcat",
        "framework_id": "nonebot",
        "bot_id": "bot-1",
        "message_type": "group",
        "conversation_id": "group-1",
    }
    assert list_items_mock.call_args.kwargs == {
        "order_by": ["-created_at", "-id"],
        "limit": 10,
    }


@pytest.mark.asyncio
async def test_list_conversation_messages_keeps_other_platform_partition_keys() -> None:
    list_items_mock = AsyncMock(return_value=[])

    with patch.object(message_store, "list_items", list_items_mock):
        await message_store.list_conversation_messages(
            platform_id="matrix",
            adapter_id="matrix.v1",
            protocol_id="matrix-client-server",
            framework_id="nonebot",
            bot_id="bot-2",
            conversation_type="room",
            conversation_id="room-2",
            limit=20,
        )

    assert list_items_mock.call_args.args[0] is MessageRecord
    assert list_items_mock.call_args.args[1] == {
        "platform_id": "matrix",
        "adapter_id": "matrix.v1",
        "protocol_id": "matrix-client-server",
        "framework_id": "nonebot",
        "bot_id": "bot-2",
        "message_type": "room",
        "conversation_id": "room-2",
    }


@pytest.mark.asyncio
async def test_cleanup_expired_messages_calls_delete_twice_and_returns_tuple() -> None:
    delete_mock = AsyncMock(side_effect=[(2, True), (1, True), (3, True), (4, True)])

    with patch.object(message_store, "delete", delete_mock):
        result = await message_store.cleanup_expired_messages(retention_days=7)

    assert result == (10, True)
    assert delete_mock.await_count == DELETE_CALL_COUNT
    assert delete_mock.call_args_list[0].args[0] is MessageRecord
    assert delete_mock.call_args_list[1].args[0] is AuditRecord
    assert delete_mock.call_args_list[2].args[0] is QQOneBotV11NoneBotEventRecord
    assert delete_mock.call_args_list[3].args[0] is QQOneBotV11NoneBotAuditRecord
    assert delete_mock.call_args_list[0].args[1] == {}
    assert delete_mock.call_args_list[1].args[1] == {}
    assert len(delete_mock.call_args_list[0].kwargs["conditions"]) == 1
    assert len(delete_mock.call_args_list[1].kwargs["conditions"]) == 1


@pytest.mark.asyncio
async def test_cleanup_expired_messages_with_zero_retention_returns_empty() -> None:
    delete_mock = AsyncMock()

    with patch.object(message_store, "delete", delete_mock):
        result = await message_store.cleanup_expired_messages(retention_days=0)

    assert result == (0, True)
    delete_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_cleanup_expired_messages_propagates_known_flag() -> None:
    delete_mock = AsyncMock(side_effect=[(1, True), (0, False), (2, True), (0, True)])

    with patch.object(message_store, "delete", delete_mock):
        result = await message_store.cleanup_expired_messages(retention_days=7)

    assert result == (3, False)
