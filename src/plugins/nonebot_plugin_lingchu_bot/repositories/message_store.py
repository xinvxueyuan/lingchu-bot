"""Repository helpers for message and audit storage records."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from ..database.models import AuditRecord, MessageRecord
from ..database.orm_crud import create, delete, get_one, list_items, update, upsert


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
    raw_message: str | None,
    raw_event: str | None,
) -> MessageRecord:
    """Create or update an incoming message record."""
    now = datetime.now(UTC)
    insert_values: dict[str, Any] = {
        "platform": platform,
        "adapter": adapter,
        "bot_id": bot_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "message_id": message_id,
        "event_type": event_type,
        "message_type": message_type,
        "text_summary": text_summary,
        "raw_message": raw_message,
        "raw_event": raw_event,
        "process_status": "received",
        "exception_summary": None,
        "created_at": now,
        "updated_at": now,
    }
    if message_id is None:
        return await create(MessageRecord, **insert_values)
    return await upsert(
        MessageRecord,
        insert_values,
        conflict_fields=[
            "platform",
            "adapter",
            "bot_id",
            "conversation_id",
            "message_id",
        ],
    )


async def record_matcher_result(  # noqa: PLR0913
    *,
    platform: str,
    adapter: str,
    bot_id: str,
    conversation_id: str | None,
    message_id: str | None,
    process_status: str,
    exception_summary: str | None = None,
) -> bool:
    """Update the processing status for a stored message record."""
    if message_id is None:
        return False
    record = await get_one(
        MessageRecord,
        {
            "platform": platform,
            "adapter": adapter,
            "bot_id": bot_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
        },
    )
    if record is None:
        return False
    await update(
        MessageRecord,
        {"id": record.id},
        {
            "process_status": process_status,
            "exception_summary": exception_summary,
            "updated_at": datetime.now(UTC),
        },
    )
    return True


async def record_api_call(  # noqa: PLR0913
    *,
    platform: str,
    adapter: str,
    bot_id: str,
    api_name: str,
    data_summary: str | None,
    result_summary: str | None,
    exception_summary: str | None,
    audit_type: str = "api_call",
) -> AuditRecord:
    """Record a platform API or lifecycle event as an audit record."""
    return await create(
        AuditRecord,
        platform=platform,
        adapter=adapter,
        bot_id=bot_id,
        audit_type=audit_type,
        event_type=api_name,
        data_summary=data_summary,
        result_summary=result_summary,
        exception_summary=exception_summary,
        created_at=datetime.now(UTC),
    )


async def list_recent_messages(
    *,
    platform: str = "qq",
    adapter: str | None = None,
    conversation_id: str | None = None,
    user_id: str | None = None,
    limit: int = 100,
) -> list[MessageRecord]:
    """List recent message records using common query dimensions."""
    filters: dict[str, Any] = {"platform": platform}
    if adapter is not None:
        filters["adapter"] = adapter
    if conversation_id is not None:
        filters["conversation_id"] = conversation_id
    if user_id is not None:
        filters["user_id"] = user_id
    return await list_items(
        MessageRecord,
        filters,
        order_by=["-created_at"],
        limit=limit,
    )


async def cleanup_expired_messages(*, retention_days: int) -> tuple[int, bool]:
    """Delete expired message and audit records."""
    if retention_days <= 0:
        return (0, True)
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    msg_count, msg_known = await delete(
        MessageRecord,
        {},
        conditions=[MessageRecord.created_at < cutoff],
    )
    audit_count, audit_known = await delete(
        AuditRecord,
        {},
        conditions=[AuditRecord.created_at < cutoff],
    )
    return (msg_count + audit_count, msg_known and audit_known)
