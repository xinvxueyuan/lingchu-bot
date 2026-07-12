"""Repository helpers for message and audit storage records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from ..database.models import (
    AuditRecord,
    MessageRecord,
    QQOneBotV11NoneBotAuditRecord,
    QQOneBotV11NoneBotEventRecord,
)
from ..database.orm_crud import create, delete, get_one, list_items, update, upsert


@dataclass(frozen=True, slots=True)
class AuditEvent:
    platform_id: str
    adapter_id: str
    bot_id: str
    api_name: str
    data_summary: str | None
    result_summary: str | None
    exception_summary: str | None
    protocol_id: str | None = None
    framework_id: str = "nonebot"
    audit_type: str = "api_call"


@dataclass(frozen=True, slots=True)
class EventStoreWrite:
    platform_id: str
    adapter_id: str
    bot_id: str
    event_type: str
    protocol_id: str | None = None
    framework_id: str = "nonebot"
    event_category: str | None = None


def event_record_model_for(
    *,
    platform_id: str,
    adapter_id: str | None,
    framework_id: str = "nonebot",
) -> type[MessageRecord | QQOneBotV11NoneBotEventRecord]:
    if (
        platform_id == "qq"
        and adapter_id == "~onebot.v11"
        and framework_id == "nonebot"
    ):
        return QQOneBotV11NoneBotEventRecord
    return MessageRecord


def audit_record_model_for(
    *,
    platform_id: str,
    adapter_id: str | None,
    framework_id: str = "nonebot",
) -> type[AuditRecord | QQOneBotV11NoneBotAuditRecord]:
    if (
        platform_id == "qq"
        and adapter_id == "~onebot.v11"
        and framework_id == "nonebot"
    ):
        return QQOneBotV11NoneBotAuditRecord
    return AuditRecord


def _event_category_from_type(event_type: str) -> str | None:
    head = event_type.split(".", maxsplit=1)[0].strip()
    return head or None


async def record_event_received(
    *,
    platform_id: str,
    adapter_id: str,
    protocol_id: str | None = None,
    bot_id: str,
    conversation_id: str | None,
    user_id: str | None,
    message_id: str | None,
    event_type: str,
    message_type: str | None,
    text_summary: str | None,
    raw_message: str | None,
    raw_event: str | None,
    event_category: str | None = None,
    framework_id: str = "nonebot",
) -> MessageRecord | QQOneBotV11NoneBotEventRecord:
    """Create or update an incoming message record."""
    now = datetime.now(UTC)
    model = event_record_model_for(
        platform_id=platform_id,
        adapter_id=adapter_id,
        framework_id=framework_id,
    )
    insert_values: dict[str, Any] = {
        "platform_id": platform_id,
        "adapter_id": adapter_id,
        "protocol_id": protocol_id,
        "framework_id": framework_id,
        "bot_id": bot_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
        "message_id": message_id,
        "event_type": event_type,
        "event_category": event_category or _event_category_from_type(event_type),
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
        return await create(model, **insert_values)
    return await upsert(
        model,
        insert_values,
        conflict_fields=[
            "platform_id",
            "adapter_id",
            "protocol_id",
            "bot_id",
            "conversation_id",
            "message_id",
        ],
    )


async def record_matcher_result(
    *,
    platform_id: str,
    adapter_id: str,
    protocol_id: str | None = None,
    bot_id: str,
    conversation_id: str | None,
    message_id: str | None,
    process_status: str,
    exception_summary: str | None = None,
    framework_id: str = "nonebot",
) -> bool:
    """Update the processing status for a stored message record."""
    if message_id is None:
        return False
    filters = {
        "platform_id": platform_id,
        "adapter_id": adapter_id,
        "bot_id": bot_id,
        "conversation_id": conversation_id,
        "message_id": message_id,
    }
    if protocol_id is not None:
        filters["protocol_id"] = protocol_id
    model = event_record_model_for(
        platform_id=platform_id,
        adapter_id=adapter_id,
        framework_id=framework_id,
    )
    record = await get_one(model, filters)
    if record is None:
        return False
    await update(
        model,
        {"id": record.id},
        {
            "process_status": process_status,
            "exception_summary": exception_summary,
            "updated_at": datetime.now(UTC),
        },
    )
    return True


async def record_api_call(
    event: AuditEvent,
) -> AuditRecord | QQOneBotV11NoneBotAuditRecord:
    """Record a platform API or lifecycle event as an audit record."""
    model = audit_record_model_for(
        platform_id=event.platform_id,
        adapter_id=event.adapter_id,
        framework_id=event.framework_id,
    )
    return await create(
        model,
        platform_id=event.platform_id,
        adapter_id=event.adapter_id,
        protocol_id=event.protocol_id,
        framework_id=event.framework_id,
        bot_id=event.bot_id,
        audit_type=event.audit_type,
        event_type=event.api_name,
        data_summary=event.data_summary,
        result_summary=event.result_summary,
        exception_summary=event.exception_summary,
        created_at=datetime.now(UTC),
    )


async def list_recent_messages(
    *,
    platform_id: str = "qq",
    adapter_id: str | None = None,
    protocol_id: str | None = None,
    bot_id: str | None = None,
    conversation_id: str | None = None,
    user_id: str | None = None,
    limit: int = 100,
    framework_id: str = "nonebot",
) -> list[MessageRecord | QQOneBotV11NoneBotEventRecord]:
    """List recent message records using common query dimensions."""
    filters: dict[str, Any] = {"platform_id": platform_id}
    if adapter_id is not None:
        filters["adapter_id"] = adapter_id
    if protocol_id is not None:
        filters["protocol_id"] = protocol_id
    if bot_id is not None:
        filters["bot_id"] = bot_id
    if conversation_id is not None:
        filters["conversation_id"] = conversation_id
    if user_id is not None:
        filters["user_id"] = user_id
    model = event_record_model_for(
        platform_id=platform_id,
        adapter_id=adapter_id,
        framework_id=framework_id,
    )
    return await list_items(
        model,
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
    partition_msg_count, partition_msg_known = await delete(
        QQOneBotV11NoneBotEventRecord,
        {},
        conditions=[QQOneBotV11NoneBotEventRecord.created_at < cutoff],
    )
    partition_audit_count, partition_audit_known = await delete(
        QQOneBotV11NoneBotAuditRecord,
        {},
        conditions=[QQOneBotV11NoneBotAuditRecord.created_at < cutoff],
    )
    return (
        msg_count + audit_count + partition_msg_count + partition_audit_count,
        msg_known and audit_known and partition_msg_known and partition_audit_known,
    )
