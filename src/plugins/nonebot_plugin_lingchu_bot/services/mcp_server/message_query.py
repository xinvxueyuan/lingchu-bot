"""Conversation-scoped stored-message query boundary."""

from __future__ import annotations

from nonebot import require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import get_session

from ...repositories import message_store as message_repository
from .authorized_message_query import MessagePage, MessagePageRequest
from .contracts import (
    ListRecentMessagesRequest,
    ListRecentMessagesResult,
    MessageEnvelope,
    TextSegment,
)


class RepositoryMessageQuery:
    """Project stored messages into the privacy-bounded MCP contract."""

    async def list_recent(
        self,
        request: ListRecentMessagesRequest,
    ) -> ListRecentMessagesResult:
        """Return one exact conversation in stable newest-first order."""
        async with get_session() as session:
            records = await message_repository.list_conversation_messages(
                session,
                platform_id=request.bot.platform_id,
                adapter_id=request.bot.adapter_id,
                protocol_id=request.bot.protocol_id,
                framework_id="nonebot",
                bot_id=request.bot.bot_id,
                conversation_type=request.conversation.conversation_type,
                conversation_id=request.conversation.conversation_id,
                limit=request.limit,
            )
        messages = tuple(
            MessageEnvelope(
                record_id=str(record.id),
                message_id=record.message_id,
                received_at=record.created_at,
                bot=request.bot,
                conversation=request.conversation,
                sender_id=record.user_id,
                segments=(TextSegment(record.text_summary),)
                if record.text_summary
                else (),
                processing_status=record.process_status,
            )
            for record in records
        )
        return ListRecentMessagesResult(messages=messages, next_cursor=None)


class RepositoryMessagePageSource:
    """Adapt stable repository pages to privacy-bounded message envelopes."""

    async def list_page(self, request: MessagePageRequest) -> MessagePage:
        """Read one stable page without exposing stored raw fields."""
        async with get_session() as session:
            (
                records,
                anchor_exists,
            ) = await message_repository.list_conversation_message_page(
                session,
                platform_id=request.bot.platform_id,
                adapter_id=request.bot.adapter_id,
                protocol_id=request.bot.protocol_id,
                framework_id="nonebot",
                bot_id=request.bot.bot_id,
                conversation_type=request.conversation.conversation_type,
                conversation_id=request.conversation.conversation_id,
                limit=request.limit,
                after_received_at=request.after.received_at
                if request.after is not None
                else None,
                after_record_id=request.after.record_id
                if request.after is not None
                else None,
                window_received_at=request.window_end.received_at
                if request.window_end is not None
                else None,
                window_record_id=request.window_end.record_id
                if request.window_end is not None
                else None,
            )
        messages = tuple(
            MessageEnvelope(
                record_id=str(record.id),
                message_id=record.message_id,
                received_at=record.created_at,
                bot=request.bot,
                conversation=request.conversation,
                sender_id=record.user_id,
                segments=(TextSegment(record.text_summary),)
                if record.text_summary
                else (),
                processing_status=record.process_status,
            )
            for record in records
        )
        return MessagePage(messages, anchor_exists)


__all__ = ("RepositoryMessagePageSource", "RepositoryMessageQuery")
