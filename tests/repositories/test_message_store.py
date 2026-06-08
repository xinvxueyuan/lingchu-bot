from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest_asyncio

from src.plugins.nonebot_plugin_lingchu_bot.database import message_storage
from src.plugins.nonebot_plugin_lingchu_bot.repositories import message_store

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

    import pytest


@pytest_asyncio.fixture(autouse=True)
async def isolated_message_store(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> AsyncIterator[None]:
    monkeypatch.setattr(message_storage, "get_plugin_data_dir", lambda: tmp_path)
    await message_storage.close_engines()
    yield
    await message_storage.close_engines()


async def test_record_event_received_creates_adapter_and_compat_databases(
    tmp_path: Path,
) -> None:
    result = await message_store.record_event_received(
        platform="qq",
        adapter="~onebot.v11",
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

    assert result.id == 1
    assert result.raw_event == '{"post_type":"message","raw_key":1}'
    assert (tmp_path / "message_store" / "qq" / "onebot_v11.db").exists()
    assert (tmp_path / "message_store" / "qq" / "compat.db").exists()

    recent = await message_store.list_recent_messages(platform="qq", limit=10)

    assert len(recent) == 1
    assert recent[0].adapter == "~onebot.v11"
    assert recent[0].raw_message == '[{"type":"text","data":{"text":"hello"}}]'


async def test_record_event_received_updates_duplicate_within_same_adapter() -> None:
    first = await message_store.record_event_received(
        platform="qq",
        adapter="~onebot.v11",
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
    second = await message_store.record_event_received(
        platform="qq",
        adapter="~onebot.v11",
        bot_id="bot-1",
        conversation_id="group-1",
        user_id="user-2",
        message_id="msg-1",
        event_type="message.group",
        message_type="group",
        text_summary="updated",
        raw_message='"updated"',
        raw_event='{"message_id":"msg-1","extra":true}',
    )

    assert second.id == first.id
    assert second.text_summary == "updated"

    recent = await message_store.list_recent_messages(platform="qq", limit=10)

    assert len(recent) == 1
    assert recent[0].text_summary == "updated"
    assert recent[0].user_id == "user-2"


async def test_same_message_id_does_not_collide_across_adapters() -> None:
    onebot = await message_store.record_event_received(
        platform="qq",
        adapter="~onebot.v11",
        bot_id="bot-1",
        conversation_id="group-1",
        user_id="user-1",
        message_id="msg-1",
        event_type="message.group",
        message_type="group",
        text_summary="onebot",
        raw_message='"onebot"',
        raw_event='{"adapter":"onebot"}',
    )
    milky = await message_store.record_event_received(
        platform="qq",
        adapter="~milky",
        bot_id="bot-1",
        conversation_id="group-1",
        user_id="user-1",
        message_id="msg-1",
        event_type="message.group",
        message_type="group",
        text_summary="milky",
        raw_message='"milky"',
        raw_event='{"adapter":"milky"}',
    )

    assert onebot.id == 1
    assert milky.id == 1

    recent = await message_store.list_recent_messages(platform="qq", limit=10)

    assert {record.adapter for record in recent} == {"~onebot.v11", "~milky"}
    assert {record.text_summary for record in recent} == {"onebot", "milky"}


async def test_record_matcher_result_updates_adapter_and_compat_records() -> None:
    await message_store.record_event_received(
        platform="qq",
        adapter="~onebot.v11",
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

    updated = await message_store.record_matcher_result(
        platform="qq",
        adapter="~onebot.v11",
        bot_id="bot-1",
        conversation_id="group-1",
        message_id="msg-1",
        process_status="handled",
    )

    assert updated is True
    adapter_rows = await message_store.list_recent_messages(
        platform="qq",
        adapter="~onebot.v11",
        limit=10,
    )
    compat_rows = await message_store.list_recent_messages(platform="qq", limit=10)
    assert adapter_rows[0].process_status == "handled"
    assert compat_rows[0].process_status == "handled"


async def test_record_api_call_writes_audit_not_message_rows() -> None:
    audit = await message_store.record_api_call(
        platform="qq",
        adapter="~onebot.v11",
        bot_id="bot-1",
        api_name="send_message",
        data_summary='{"message":"hello"}',
        result_summary='{"message_id":"out-1"}',
        exception_summary=None,
    )

    assert audit.audit_type == "api_call"
    assert audit.event_type == "send_message"
    assert await message_store.list_recent_messages(platform="qq", limit=10) == []


async def test_cleanup_expired_messages_deletes_message_compat_and_audit_rows() -> None:
    message = await message_store.record_event_received(
        platform="qq",
        adapter="~onebot.v11",
        bot_id="bot-1",
        conversation_id="group-1",
        user_id="user-1",
        message_id="msg-1",
        event_type="message.group",
        message_type="group",
        text_summary="old",
        raw_message='"old"',
        raw_event='{"message_id":"msg-1"}',
    )
    await message_store.record_api_call(
        platform="qq",
        adapter="~onebot.v11",
        bot_id="bot-1",
        api_name="send_message",
        data_summary=None,
        result_summary=None,
        exception_summary=None,
    )
    target = message_storage.storage_target("qq", "~onebot.v11")
    old = datetime.now(UTC) - timedelta(days=10)
    async with message_storage.session_for(target.adapter_db) as session:
        adapter_record = await session.get(message_storage.MessageRecord, message.id)
        audit_record = await session.get(message_storage.AuditRecord, 1)
        assert adapter_record is not None
        assert audit_record is not None
        adapter_record.created_at = old
        audit_record.created_at = old
    async with message_storage.session_for(target.compat_db) as session:
        compat_record = await session.get(message_storage.PlatformMessageRecord, 1)
        assert compat_record is not None
        compat_record.created_at = old

    result = await message_store.cleanup_expired_messages(retention_days=7)

    assert result == (3, True)
    assert await message_store.list_recent_messages(platform="qq", limit=10) == []
