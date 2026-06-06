"""Repository helpers for message storage records."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from ..database import orm_crud
from ..database.models import MessageRecord


async def record_event_received(  # noqa: PLR0913
    *,
    platform: str,
    adapter: str,
    bot_id: str,
    conversation_id: str | None,
    user_id: str | None,
    message_id: str | None,
    event_type: str,
    message_type: str | None,
    text_summary: str | None,
) -> MessageRecord:
    """Create or update the message record for an incoming event."""
    fields: dict[str, Any] = {
        "platform": platform,
        "adapter": adapter,
        "bot_id": bot_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "message_id": message_id,
        "event_type": event_type,
        "message_type": message_type,
        "text_summary": text_summary,
        "process_status": "received",
        "updated_at": datetime.now(UTC),
    }
    if message_id is None:
        return await orm_crud.create(
            MessageRecord,
            created_at=datetime.now(UTC),
            **fields,
        )

    lookup = {
        "platform": platform,
        "bot_id": bot_id,
        "conversation_id": conversation_id,
        "message_id": message_id,
    }
    obj, created = await orm_crud.get_or_create(
        MessageRecord,
        defaults={**fields, "created_at": datetime.now(UTC)},
        platform=platform,
        bot_id=bot_id,
        conversation_id=conversation_id,
        message_id=message_id,
    )
    if created:
        return obj

    await orm_crud.update(MessageRecord, lookup, fields)
    refreshed = await orm_crud.get_one(MessageRecord, lookup)
    return refreshed or obj


async def record_matcher_result(  # noqa: PLR0913
    *,
    platform: str,
    bot_id: str,
    conversation_id: str | None,
    message_id: str | None,
    process_status: str,
    exception_summary: str | None = None,
) -> bool:
    """Update the processing status for a stored event."""
    if message_id is None:
        return False
    affected, known = await orm_crud.update(
        MessageRecord,
        {
            "platform": platform,
            "bot_id": bot_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
        },
        {
            "process_status": process_status,
            "exception_summary": exception_summary,
            "updated_at": datetime.now(UTC),
        },
    )
    return not known or affected > 0


async def record_api_call(  # noqa: PLR0913
    *,
    platform: str,
    adapter: str,
    bot_id: str,
    api_name: str,
    data_summary: str | None,
    result_summary: str | None,
    exception_summary: str | None,
) -> MessageRecord:
    """Record a platform API call as an auxiliary message-store event."""
    status = "api_failed" if exception_summary else "api_called"
    return await orm_crud.create(
        MessageRecord,
        platform=platform,
        adapter=adapter,
        bot_id=bot_id,
        conversation_id=None,
        user_id=None,
        message_id=None,
        event_type="api_called",
        message_type="api",
        text_summary=data_summary,
        process_status=status,
        exception_summary=exception_summary,
        api_name=api_name,
        api_result_summary=result_summary,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


async def list_recent_messages(
    *,
    conversation_id: str | None = None,
    user_id: str | None = None,
    limit: int = 100,
) -> list[MessageRecord]:
    """List recent message records using common query dimensions."""
    filters: dict[str, Any] = {}
    if conversation_id is not None:
        filters["conversation_id"] = conversation_id
    if user_id is not None:
        filters["user_id"] = user_id
    return await orm_crud.list_items(
        MessageRecord,
        filters=filters,
        conditions=None,
        order_by=["-created_at"],
        limit=limit,
    )


async def cleanup_expired_messages(*, retention_days: int) -> tuple[int, bool]:
    """Delete records older than the configured retention window."""
    if retention_days <= 0:
        return (0, True)
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    return await orm_crud.delete(
        MessageRecord,
        {},
        conditions=[MessageRecord.created_at < cutoff],
    )
