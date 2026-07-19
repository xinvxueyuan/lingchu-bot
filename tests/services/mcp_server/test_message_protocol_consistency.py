from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.hooks import adapters
from src.plugins.nonebot_plugin_lingchu_bot.services import message_store
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server import message_query
from src.plugins.nonebot_plugin_lingchu_bot.services.mcp_server.contracts import (
    BotAddress,
    ConversationAddress,
    ListRecentMessagesRequest,
)


@pytest.mark.asyncio
async def test_onebot_default_protocol_is_consistent_from_ingestion_to_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = SimpleNamespace(
        message_store_enabled=True,
        message_store_summary_limit=500,
    )
    monkeypatch.setattr(adapters, "runtime_config", config)
    monkeypatch.setattr(message_store, "runtime_config", config)
    record_event = AsyncMock()
    monkeypatch.setattr(
        message_store.repository,
        "record_event_received",
        record_event,
    )
    list_messages = AsyncMock(return_value=[])
    monkeypatch.setattr(
        message_query.message_repository,
        "list_conversation_messages",
        list_messages,
    )
    bot = MagicMock(self_id="bot-1")
    bot.adapter.get_name.return_value = "OneBot V11"
    event = MagicMock(
        message_id="message-1",
        message_type="group",
        group_id="group-1",
        data=SimpleNamespace(),
    )
    event.get_event_name.return_value = "message.group"
    event.get_type.return_value = "message"
    event.get_user_id.return_value = "user-1"
    event.get_plaintext.return_value = "hello"
    event.get_message.return_value = "hello"

    normalized = adapters.normalize_message_event(bot, event)
    assert normalized is not None
    await message_store.handle_event_received(normalized)
    await message_query.RepositoryMessageQuery().list_recent(
        ListRecentMessagesRequest(
            bot=BotAddress("qq", "~onebot.v11", "default", "bot-1"),
            conversation=ConversationAddress("group", "group-1"),
        )
    )

    assert record_event.await_args is not None
    assert record_event.await_args.kwargs["protocol_id"] == "default"
    assert list_messages.await_args is not None
    assert list_messages.await_args.kwargs["protocol_id"] == "default"
