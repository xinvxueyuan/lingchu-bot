"""Repository helpers for adapter-scoped message storage records."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from ..database import message_storage as storage
from ..database.message_storage import AuditRecord, MessageRecord, PlatformMessageRecord


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
    """Create or update an incoming message in its adapter database."""
    target = storage.storage_target(platform, adapter)
    now = datetime.now(UTC)
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
        "raw_message": raw_message,
        "raw_event": raw_event,
        "process_status": "received",
        "exception_summary": None,
        "updated_at": now,
    }
    async with storage.session_for(target.adapter_db) as session:
        record: MessageRecord | None = None
        if message_id is not None:
            record = await storage.fetch_one_message(
                session,
                platform=platform,
                adapter=adapter,
                bot_id=bot_id,
                conversation_id=conversation_id,
                message_id=message_id,
            )
        if record is None:
            record = MessageRecord(created_at=now, **fields)
            session.add(record)
            await session.flush()
        else:
            for key, value in fields.items():
                setattr(record, key, value)
            await session.flush()
        await session.refresh(record)

    await _upsert_platform_projection(target, record)
    return record


async def _upsert_platform_projection(
    target: storage.StorageTarget,
    record: MessageRecord,
) -> None:
    fields = storage.copy_message_fields(record)
    async with storage.session_for(target.compat_db) as session:
        result = await session.execute(
            select(PlatformMessageRecord).where(
                PlatformMessageRecord.source_adapter_id == target.adapter_id,
                PlatformMessageRecord.source_record_id == record.id,
            )
        )
        projection = result.scalar_one_or_none()
        if projection is None:
            session.add(
                PlatformMessageRecord(
                    source_adapter_id=target.adapter_id,
                    source_record_id=record.id,
                    **fields,
                )
            )
            return
        for key, value in fields.items():
            setattr(projection, key, value)


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
    """Update the processing status for a stored adapter message."""
    if message_id is None:
        return False
    target = storage.storage_target(platform, adapter)
    async with storage.session_for(target.adapter_db) as session:
        record = await storage.fetch_one_message(
            session,
            platform=platform,
            adapter=adapter,
            bot_id=bot_id,
            conversation_id=conversation_id,
            message_id=message_id,
        )
        if record is None:
            return False
        record.process_status = process_status
        record.exception_summary = exception_summary
        record.updated_at = datetime.now(UTC)
        await session.flush()
        await session.refresh(record)
    await _upsert_platform_projection(target, record)
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
    """Record a platform API or lifecycle event in adapter audit storage."""
    target = storage.storage_target(platform, adapter)
    async with storage.session_for(target.adapter_db) as session:
        record = AuditRecord(
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
        session.add(record)
        await session.flush()
        await session.refresh(record)
        return record


async def list_recent_messages(
    *,
    platform: str = "qq",
    adapter: str | None = None,
    conversation_id: str | None = None,
    user_id: str | None = None,
    limit: int = 100,
) -> list[MessageRecord | PlatformMessageRecord]:
    """List recent message records using common query dimensions."""
    if adapter is not None:
        target = storage.storage_target(platform, adapter)
        model: type[MessageRecord | PlatformMessageRecord] = MessageRecord
        db_path = target.adapter_db
    else:
        platform_adapter = storage.adapters_for_platform(platform)[0]
        target = storage.storage_target(platform, platform_adapter)
        model = PlatformMessageRecord
        db_path = target.compat_db

    stmt = select(model)
    if conversation_id is not None:
        stmt = stmt.where(model.conversation_id == conversation_id)
    if user_id is not None:
        stmt = stmt.where(model.user_id == user_id)
    stmt = stmt.order_by(model.created_at.desc()).limit(limit)

    async with storage.session_for(db_path) as session:
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def cleanup_expired_messages(*, retention_days: int) -> tuple[int, bool]:
    """Delete expired message and audit records across all known storage DBs."""
    if retention_days <= 0:
        return (0, True)
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    deleted = 0
    seen_compat: set[Any] = set()
    for target in storage.iter_known_targets():
        async with storage.session_for(target.adapter_db) as session:
            deleted += await storage.cleanup_table(session, MessageRecord, cutoff)
            deleted += await storage.cleanup_table(session, AuditRecord, cutoff)
        if target.compat_db in seen_compat:
            continue
        seen_compat.add(target.compat_db)
        async with storage.session_for(target.compat_db) as session:
            deleted += await storage.cleanup_table(
                session,
                PlatformMessageRecord,
                cutoff,
            )
    return (deleted, True)
