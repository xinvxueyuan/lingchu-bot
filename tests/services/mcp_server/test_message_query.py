from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server import message_query
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.authorized_message_query import (
    MessagePageRequest,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.contracts import (
    BotAddress,
    ConversationAddress,
    ListRecentMessagesRequest,
    TextSegment,
)
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.cursor import (
    CursorPosition,
)


@pytest.mark.asyncio
async def test_repository_message_query_projects_privacy_bounded_envelopes() -> None:
    received_at = datetime(2026, 7, 18, 3, 4, tzinfo=UTC)
    record = SimpleNamespace(
        id=42,
        message_id="message-42",
        created_at=received_at,
        user_id="sender-7",
        text_summary="hello",
        process_status="processed",
        raw_message="SECRET RAW MESSAGE",
        raw_event="SECRET RAW EVENT",
        exception_summary="SECRET TRACEBACK",
    )
    system_record = SimpleNamespace(
        id=41,
        message_id=None,
        created_at=datetime(2026, 7, 18, 3, 3, tzinfo=UTC),
        user_id=None,
        text_summary=None,
        process_status="received",
        raw_message="SECRET SYSTEM RAW MESSAGE",
        raw_event="SECRET SYSTEM RAW EVENT",
        exception_summary=None,
    )
    request = ListRecentMessagesRequest(
        bot=BotAddress("qq", "~onebot.v11", "napcat", "bot-1"),
        conversation=ConversationAddress("group", "group-1"),
        limit=10,
    )

    with patch.object(
        message_query.message_repository,
        "list_conversation_messages",
        AsyncMock(return_value=[record, system_record]),
    ) as list_mock:
        result = await message_query.RepositoryMessageQuery().list_recent(request)

    list_mock.assert_awaited_once_with(
        platform_id="qq",
        adapter_id="~onebot.v11",
        protocol_id="napcat",
        framework_id="nonebot",
        bot_id="bot-1",
        conversation_type="group",
        conversation_id="group-1",
        limit=10,
    )
    assert result.next_cursor is None
    assert result.messages[0].record_id == "42"
    assert result.messages[0].received_at == received_at
    assert result.messages[0].sender_id == "sender-7"
    assert result.messages[0].segments == (TextSegment("hello"),)
    assert result.messages[0].processing_status == "processed"
    assert result.messages[1].sender_id is None
    assert result.messages[1].segments == ()
    assert "SECRET" not in repr(result)


@pytest.mark.asyncio
async def test_repository_page_source_projects_stable_window_page() -> None:
    received_at = datetime(2026, 7, 18, 3, 4, tzinfo=UTC)
    record = SimpleNamespace(
        id=42,
        message_id="message-42",
        created_at=received_at,
        user_id="sender-7",
        text_summary="hello",
        process_status="processed",
        raw_message="SECRET RAW MESSAGE",
        raw_event="SECRET RAW EVENT",
    )
    request = MessagePageRequest(
        BotAddress("qq", "~onebot.v11", "napcat", "bot-1"),
        ConversationAddress("group", "group-1"),
        3,
        CursorPosition(datetime(2026, 7, 18, 3, 5, tzinfo=UTC), "50"),
        CursorPosition(datetime(2026, 7, 18, 3, 10, tzinfo=UTC), "80"),
    )
    assert request.after is not None
    assert request.window_end is not None

    with patch.object(
        message_query.message_repository,
        "list_conversation_message_page",
        AsyncMock(return_value=([record], True)),
        create=True,
    ) as list_mock:
        page = await message_query.RepositoryMessagePageSource().list_page(request)

    list_mock.assert_awaited_once_with(
        platform_id="qq",
        adapter_id="~onebot.v11",
        protocol_id="napcat",
        framework_id="nonebot",
        bot_id="bot-1",
        conversation_type="group",
        conversation_id="group-1",
        limit=3,
        after_received_at=request.after.received_at,
        after_record_id="50",
        window_received_at=request.window_end.received_at,
        window_record_id="80",
    )
    assert page.anchor_exists is True
    assert page.messages[0].record_id == "42"
    assert "SECRET" not in repr(page)
