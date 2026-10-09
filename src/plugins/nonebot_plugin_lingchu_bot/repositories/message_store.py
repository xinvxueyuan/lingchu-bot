"""Repository helpers for message and audit storage records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, or_

from ..database.models import (
    AuditRecord,
    MessageRecord,
    QQOneBotV11NoneBotAuditRecord,
    QQOneBotV11NoneBotEventRecord,
)
from ..database.orm_crud import create, delete, get_one, list_items, update, upsert

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session


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
    session: AsyncSession | async_scoped_session[AsyncSession],
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
        return await create(session, model, **insert_values)
    return await upsert(
        session,
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
    session: AsyncSession | async_scoped_session[AsyncSession],
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
    record = await get_one(session, model, filters)
    if record is None:
        return False
    await update(
        session,
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
    session: AsyncSession | async_scoped_session[AsyncSession],
    event: AuditEvent,
) -> AuditRecord | QQOneBotV11NoneBotAuditRecord:
    """Record a platform API or lifecycle event as an audit record."""
    model = audit_record_model_for(
        platform_id=event.platform_id,
        adapter_id=event.adapter_id,
        framework_id=event.framework_id,
    )
    return await create(
        session,
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
    session: AsyncSession | async_scoped_session[AsyncSession],
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
        session,
        model,
        filters,
        order_by=["-created_at"],
        limit=limit,
    )


async def list_conversation_messages(
    session: AsyncSession | async_scoped_session[AsyncSession],
    *,
    platform_id: str,
    adapter_id: str,
    protocol_id: str,
    framework_id: str,
    bot_id: str,
    conversation_type: str,
    conversation_id: str,
    limit: int,
) -> list[MessageRecord | QQOneBotV11NoneBotEventRecord]:
    """List one exact conversation before applying a bounded page."""
    model = event_record_model_for(
        platform_id=platform_id,
        adapter_id=adapter_id,
        framework_id=framework_id,
    )
    return await list_items(
        session,
        model,
        {
            "platform_id": platform_id,
            "adapter_id": adapter_id,
            "protocol_id": protocol_id,
            "framework_id": framework_id,
            "bot_id": bot_id,
            "message_type": conversation_type,
            "conversation_id": conversation_id,
        },
        order_by=["-created_at", "-id"],
        limit=limit,
    )


async def list_conversation_message_page(
    session: AsyncSession | async_scoped_session[AsyncSession],
    *,
    platform_id: str,
    adapter_id: str,
    protocol_id: str,
    framework_id: str,
    bot_id: str,
    conversation_type: str,
    conversation_id: str,
    limit: int,
    after_received_at: datetime | None,
    after_record_id: str | None,
    window_received_at: datetime | None,
    window_record_id: str | None,
) -> tuple[
    list[MessageRecord | QQOneBotV11NoneBotEventRecord],
    bool,
]:
    """Read one exact conversation within a frozen keyset window."""
    model = event_record_model_for(
        platform_id=platform_id,
        adapter_id=adapter_id,
        framework_id=framework_id,
    )
    filters: dict[str, Any] = {
        "platform_id": platform_id,
        "adapter_id": adapter_id,
        "protocol_id": protocol_id,
        "framework_id": framework_id,
        "bot_id": bot_id,
        "message_type": conversation_type,
        "conversation_id": conversation_id,
    }
    try:
        after_id = int(after_record_id) if after_record_id is not None else None
        window_id = int(window_record_id) if window_record_id is not None else None
    except ValueError:
        return ([], False)
    anchor_exists = True
    if after_received_at is not None and after_id is not None:
        anchor_exists = bool(
            await list_items(
                session,
                model,
                filters,
                conditions=[
                    model.created_at == after_received_at,
                    model.id == after_id,
                ],
                limit=1,
            )
        )
    conditions = []
    if window_received_at is not None and window_id is not None:
        conditions.append(
            or_(
                model.created_at < window_received_at,
                and_(
                    model.created_at == window_received_at,
                    model.id <= window_id,
                ),
            )
        )
    if after_received_at is not None and after_id is not None:
        conditions.append(
            or_(
                model.created_at < after_received_at,
                and_(
                    model.created_at == after_received_at,
                    model.id < after_id,
                ),
            )
        )
    records = await list_items(
        session,
        model,
        filters,
        conditions=conditions,
        order_by=["-created_at", "-id"],
        limit=limit,
    )
    if anchor_exists and after_received_at is not None and after_id is not None:
        anchor_exists = bool(
            await list_items(
                session,
                model,
                filters,
                conditions=[
                    model.created_at == after_received_at,
                    model.id == after_id,
                ],
                limit=1,
            )
        )
    return (records, anchor_exists)


async def cleanup_expired_messages(
    session: AsyncSession | async_scoped_session[AsyncSession],
    *,
    retention_days: int,
) -> tuple[int, bool]:
    """Delete expired message and audit records."""
    if retention_days <= 0:
        return (0, True)
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    msg_count, msg_known = await delete(
        session,
        MessageRecord,
        {},
        conditions=[MessageRecord.created_at < cutoff],
    )
    audit_count, audit_known = await delete(
        session,
        AuditRecord,
        {},
        conditions=[AuditRecord.created_at < cutoff],
    )
    partition_msg_count, partition_msg_known = await delete(
        session,
        QQOneBotV11NoneBotEventRecord,
        {},
        conditions=[QQOneBotV11NoneBotEventRecord.created_at < cutoff],
    )
    partition_audit_count, partition_audit_known = await delete(
        session,
        QQOneBotV11NoneBotAuditRecord,
        {},
        conditions=[QQOneBotV11NoneBotAuditRecord.created_at < cutoff],
    )
    return (
        msg_count + audit_count + partition_msg_count + partition_audit_count,
        msg_known and audit_known and partition_msg_known and partition_audit_known,
    )


async def list_recent_command_audits(
    session: AsyncSession | async_scoped_session[AsyncSession],
    *,
    action: str,
    platform_id: str = "qq",
    adapter_id: str | None = None,
    bot_id: str | None = None,
    group_id: int | None = None,
    limit: int = 200,
) -> list[QQOneBotV11NoneBotAuditRecord]:
    """列出某条命令最近的审计记录，按时间倒序。

    只做**粗筛**：``data_summary`` 是自由文本（形如
    ``operator=…, target=…, action=…, group=…``），没有结构化的 group/target 列，
    因此这里只按 ``event_type`` 精确过滤、可选按群号做**子串**粗筛，并给出上限；
    调用方必须解析 summary 后再按 group / target 二次过滤 —— 群号可能恰好出现在
    reason 文本里。

    ``group_id`` 之所以要在这里（而不是只在调用方）过滤：结果是**先 LIMIT 再**
    交给调用方的，若不做群号粗筛，同一个群里更早、仍在保留期内的记录会被后来的
    其他群的记录挤出窗口，表现为「明明有记录却显示未知」。子串匹配可能多带几行，
    多带是安全的（调用方仍会精确比对），漏掉才是问题。

    注意列名：命令审计写入时把 ``AuditEvent.api_name`` 存进了 **``event_type``**
    列（见 :func:`record_api_call`），模型上并没有 ``api_name`` 列 —— 传错的键名会
    让 :func:`list_items` 抛 ``ValueError``（不是 ``DatabaseError``）。

    审计记录受消息保留策略约束（``cleanup_expired_messages`` 会一并删除），
    所以超出保留期的禁言在这里查不到，调用方需要按「未知」降级。
    """
    filters: dict[str, Any] = {
        "platform_id": platform_id,
        "audit_type": "command",
        "event_type": f"command:{action}",
    }
    if adapter_id is not None:
        filters["adapter_id"] = adapter_id
    if bot_id is not None:
        filters["bot_id"] = bot_id

    conditions = None
    if group_id is not None:
        conditions = [
            QQOneBotV11NoneBotAuditRecord.data_summary.like(f"%group={group_id}%")
        ]

    return await list_items(
        session,
        QQOneBotV11NoneBotAuditRecord,
        filters,
        order_by=["-created_at"],
        conditions=conditions,
        limit=limit,
    )
