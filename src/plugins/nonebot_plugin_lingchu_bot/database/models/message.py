"""Message and audit record ORM models."""

from __future__ import annotations

from datetime import UTC, datetime

from nonebot import require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import Model
from sqlalchemy import (
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(UTC)


class MessageRecord(Model):
    """Real incoming message event stored in the global ORM database."""

    __tablename__ = "lingchu_message_records"
    __table_args__ = (
        UniqueConstraint(
            "platform_id",
            "adapter_id",
            "protocol_id",
            "bot_id",
            "conversation_id",
            "message_id",
            name="uq_lingchu_message_record_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[str] = mapped_column(String(64), index=True)
    adapter_id: Mapped[str] = mapped_column(String(64), index=True)
    protocol_id: Mapped[str | None] = mapped_column(String(64), index=True)
    framework_id: Mapped[str] = mapped_column(String(64), default="nonebot", index=True)
    bot_id: Mapped[str] = mapped_column(String(128), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(128), index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), index=True)
    message_id: Mapped[str | None] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    event_category: Mapped[str | None] = mapped_column(String(64), index=True)
    message_type: Mapped[str | None] = mapped_column(String(64), index=True)
    text_summary: Mapped[str | None] = mapped_column(Text)
    raw_message: Mapped[str | None] = mapped_column(Text)
    raw_event: Mapped[str | None] = mapped_column(Text)
    process_status: Mapped[str] = mapped_column(
        String(32),
        default="received",
        index=True,
    )
    exception_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        index=True,
    )


class AuditRecord(Model):
    """Audit event for API calls and bot lifecycle events."""

    __tablename__ = "lingchu_audit_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[str] = mapped_column(String(64), index=True)
    adapter_id: Mapped[str] = mapped_column(String(64), index=True)
    protocol_id: Mapped[str | None] = mapped_column(String(64), index=True)
    framework_id: Mapped[str] = mapped_column(String(64), default="nonebot", index=True)
    bot_id: Mapped[str] = mapped_column(String(128), index=True)
    audit_type: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    data_summary: Mapped[str | None] = mapped_column(Text)
    result_summary: Mapped[str | None] = mapped_column(Text)
    exception_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )


class QQOneBotV11NoneBotEventRecord(Model):
    """Incoming QQ OneBot V11 event stored in the NoneBot partition."""

    __tablename__ = "lingchu_qq_onebot_v11_nonebot_event_records"
    __table_args__ = (
        UniqueConstraint(
            "platform_id",
            "adapter_id",
            "protocol_id",
            "bot_id",
            "conversation_id",
            "message_id",
            name="uq_lingchu_qq_ob11_nb_event_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[str] = mapped_column(String(64), index=True)
    adapter_id: Mapped[str] = mapped_column(String(64), index=True)
    protocol_id: Mapped[str | None] = mapped_column(String(64), index=True)
    framework_id: Mapped[str] = mapped_column(String(64), default="nonebot", index=True)
    bot_id: Mapped[str] = mapped_column(String(128), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(128), index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), index=True)
    message_id: Mapped[str | None] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    event_category: Mapped[str | None] = mapped_column(String(64), index=True)
    message_type: Mapped[str | None] = mapped_column(String(64), index=True)
    text_summary: Mapped[str | None] = mapped_column(Text)
    raw_message: Mapped[str | None] = mapped_column(Text)
    raw_event: Mapped[str | None] = mapped_column(Text)
    process_status: Mapped[str] = mapped_column(
        String(32),
        default="received",
        index=True,
    )
    exception_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        index=True,
    )


class QQOneBotV11NoneBotAuditRecord(Model):
    """QQ OneBot V11 API and lifecycle audit event in the NoneBot partition."""

    __tablename__ = "lingchu_qq_onebot_v11_nonebot_audit_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[str] = mapped_column(String(64), index=True)
    adapter_id: Mapped[str] = mapped_column(String(64), index=True)
    protocol_id: Mapped[str | None] = mapped_column(String(64), index=True)
    framework_id: Mapped[str] = mapped_column(String(64), default="nonebot", index=True)
    bot_id: Mapped[str] = mapped_column(String(128), index=True)
    audit_type: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    data_summary: Mapped[str | None] = mapped_column(Text)
    result_summary: Mapped[str | None] = mapped_column(Text)
    exception_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )
