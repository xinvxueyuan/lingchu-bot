"""ORM models for Lingchu Bot runtime data."""

from __future__ import annotations

from datetime import UTC, datetime

from nonebot import require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import Model
from sqlalchemy import (
    Boolean,
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
    bot_id: Mapped[str] = mapped_column(String(128), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(128), index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), index=True)
    message_id: Mapped[str | None] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
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
    protocol_id: Mapped[str | None] = mapped_column(String(64), index=True)
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


class Platform(Model):
    """Platform registry entry seeded from registry.py."""

    __tablename__ = "lingchu_platforms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(64))
    capabilities: Mapped[str] = mapped_column(Text)  # JSON array of capability strings
    implemented: Mapped[bool] = mapped_column(Boolean, default=True)
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


class Adapter(Model):
    """Adapter registry entry seeded from registry.py."""

    __tablename__ = "lingchu_adapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    adapter_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    platform_id: Mapped[str] = mapped_column(String(64), index=True)
    display_name: Mapped[str] = mapped_column(String(64))
    nonebot_adapter_id: Mapped[str] = mapped_column(String(64))
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


class ProtocolImplementation(Model):
    """Protocol implementation registry entry seeded from adapter modules."""

    __tablename__ = "lingchu_protocol_implementations"
    __table_args__ = (
        UniqueConstraint(
            "adapter_id",
            "protocol_id",
            name="uq_lingchu_protocol_implementation_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    protocol_id: Mapped[str] = mapped_column(String(64), index=True)
    adapter_id: Mapped[str] = mapped_column(String(64), index=True)
    display_name: Mapped[str] = mapped_column(String(64))
    module_path: Mapped[str] = mapped_column(String(256))
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


class IdentityUser(Model):
    """Lingchu-wide user identity used across platform accounts."""

    __tablename__ = "lingchu_identity_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    nickname: Mapped[str] = mapped_column(String(128))
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


class PlatformAccount(Model):
    """Binding between a Lingchu UID and one platform account."""

    __tablename__ = "lingchu_platform_accounts"
    __table_args__ = (
        UniqueConstraint(
            "platform_id",
            "account_id",
            name="uq_lingchu_platform_account_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(64), index=True)
    platform_id: Mapped[str] = mapped_column(String(64), index=True)
    account_id: Mapped[str] = mapped_column(String(128), index=True)
    account_type: Mapped[str] = mapped_column(String(64), default="user", index=True)
    display_name: Mapped[str | None] = mapped_column(String(128))
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


class PlatformIdentityGroup(Model):
    """Platform-scoped identity group, including builtin and custom groups."""

    __tablename__ = "lingchu_platform_identity_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    platform_id: Mapped[str] = mapped_column(String(64), index=True)
    parent_group_id: Mapped[str | None] = mapped_column(String(128), index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    builtin: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    managed_by: Mapped[str | None] = mapped_column(String(64), index=True)
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


class IdentityMembership(Model):
    """Membership of a UID in an identity group, optionally scoped."""

    __tablename__ = "lingchu_identity_memberships"
    __table_args__ = (
        UniqueConstraint(
            "uid",
            "group_id",
            "scope_type",
            "scope_id",
            name="uq_lingchu_identity_membership_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(64), index=True)
    group_id: Mapped[str] = mapped_column(String(128), index=True)
    scope_type: Mapped[str] = mapped_column(String(64), default="global", index=True)
    scope_id: Mapped[str | None] = mapped_column(String(128), index=True)
    source: Mapped[str] = mapped_column(String(64), default="manual", index=True)
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


class PermissionGrant(Model):
    """Allow-list grant from an identity group to a command key."""

    __tablename__ = "lingchu_permission_grants"
    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "command_key",
            name="uq_lingchu_permission_grant_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[str] = mapped_column(String(128), index=True)
    command_key: Mapped[str] = mapped_column(String(128), index=True)
    effect: Mapped[str] = mapped_column(String(16), default="allow", index=True)
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
