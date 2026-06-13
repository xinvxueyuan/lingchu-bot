"""ORM models for Lingchu Bot runtime data."""

from __future__ import annotations

from datetime import UTC, datetime

from nonebot import require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import Model
from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(UTC)


class MessageRecord(Model):
    """Stored message-processing record.

    The first version stores queryable metadata plus a short text summary only.
    It intentionally does not persist raw adapter event payloads.
    """

    __tablename__ = "lingchu_message_records"
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "bot_id",
            "conversation_id",
            "message_id",
            name="uq_lingchu_message_record_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(64), index=True)
    adapter: Mapped[str] = mapped_column(String(64), index=True)
    bot_id: Mapped[str] = mapped_column(String(128), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(128), index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), index=True)
    message_id: Mapped[str | None] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    message_type: Mapped[str | None] = mapped_column(String(64), index=True)
    text_summary: Mapped[str | None] = mapped_column(Text)
    process_status: Mapped[str] = mapped_column(
        String(32),
        default="received",
        index=True,
    )
    exception_summary: Mapped[str | None] = mapped_column(Text)
    api_name: Mapped[str | None] = mapped_column(String(128), index=True)
    api_result_summary: Mapped[str | None] = mapped_column(Text)
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


class BlocklistEntry(Model):
    """Stored group/global blocklist entry for platform users."""

    __tablename__ = "lingchu_blocklist_entries"
    __table_args__ = (
        UniqueConstraint(
            "platform_id",
            "adapter_id",
            "bot_id",
            "scope",
            "scope_key",
            "user_id",
            name="uq_lingchu_blocklist_entry_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[str] = mapped_column(String(64), index=True)
    adapter_id: Mapped[str] = mapped_column(String(64), index=True)
    bot_id: Mapped[str] = mapped_column(String(128), index=True)
    scope: Mapped[str] = mapped_column(String(32), index=True)
    scope_key: Mapped[str] = mapped_column(String(128), index=True)
    group_id: Mapped[str | None] = mapped_column(String(128), index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    operator_id: Mapped[str | None] = mapped_column(String(128), index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
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
