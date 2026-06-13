"""ORM models for Lingchu Bot runtime data."""

from __future__ import annotations

from datetime import UTC, datetime

from nonebot import require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import Model
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
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


class PermissionNode(Model):
    """Materialized permission tree node."""

    __tablename__ = "lingchu_permission_nodes"
    __table_args__ = (UniqueConstraint("path", name="uq_lingchu_permission_node_path"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String(512), index=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    platform_id: Mapped[str | None] = mapped_column(String(64), index=True)
    adapter_id: Mapped[str | None] = mapped_column(String(64), index=True)
    implementation_name: Mapped[str | None] = mapped_column(String(128), index=True)
    command_key: Mapped[str | None] = mapped_column(String(128), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), index=True)
    title: Mapped[str | None] = mapped_column(String(256))
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
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


class PermissionGroup(Model):
    """Internal virtual identity group."""

    __tablename__ = "lingchu_permission_groups"
    __table_args__ = (UniqueConstraint("key", name="uq_lingchu_permission_group_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(256))
    parent_id: Mapped[int | None] = mapped_column(Integer, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
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


class PermissionGroupMember(Model):
    """Binding from a platform user to an internal permission group."""

    __tablename__ = "lingchu_permission_group_members"
    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "platform_id",
            "user_id",
            "resource_type",
            "resource_id",
            name="uq_lingchu_permission_group_member_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("lingchu_permission_groups.id", ondelete="CASCADE"),
        index=True,
    )
    platform_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), index=True)
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


class PermissionGrant(Model):
    """Grant a group access to a permission node subtree."""

    __tablename__ = "lingchu_permission_grants"
    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "node_id",
            "resource_type",
            "resource_id",
            name="uq_lingchu_permission_grant_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("lingchu_permission_groups.id", ondelete="CASCADE"),
        index=True,
    )
    node_id: Mapped[int] = mapped_column(
        ForeignKey("lingchu_permission_nodes.id", ondelete="CASCADE"),
        index=True,
    )
    resource_type: Mapped[str | None] = mapped_column(String(64), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
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


class NativeRoleMapping(Model):
    """Map native platform roles to internal permission groups."""

    __tablename__ = "lingchu_native_role_mappings"
    __table_args__ = (
        UniqueConstraint(
            "platform_id",
            "adapter_id",
            "resource_type",
            "native_role",
            name="uq_lingchu_native_role_mapping_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[str] = mapped_column(String(64), index=True)
    adapter_id: Mapped[str | None] = mapped_column(String(64), index=True)
    resource_type: Mapped[str] = mapped_column(String(64), index=True)
    native_role: Mapped[str] = mapped_column(String(64), index=True)
    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("lingchu_permission_groups.id", ondelete="CASCADE"),
        index=True,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
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


class CapabilityContract(Model):
    """Runtime capability contract for a platform/adapter/implementation command."""

    __tablename__ = "lingchu_capability_contracts"
    __table_args__ = (
        UniqueConstraint(
            "platform_id",
            "adapter_id",
            "implementation_name",
            "command_key",
            name="uq_lingchu_capability_contract_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[str] = mapped_column(String(64), index=True)
    adapter_id: Mapped[str] = mapped_column(String(64), index=True)
    implementation_name: Mapped[str | None] = mapped_column(String(128), index=True)
    command_key: Mapped[str] = mapped_column(String(128), index=True)
    capability: Mapped[str] = mapped_column(String(128), index=True)
    minimum_version: Mapped[str | None] = mapped_column(String(64))
    protocol_version: Mapped[str | None] = mapped_column(String(64))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
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


class PermissionAuditLog(Model):
    """Internal audit log for permission and impersonated platform operations."""

    __tablename__ = "lingchu_permission_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[str | None] = mapped_column(String(64), index=True)
    adapter_id: Mapped[str | None] = mapped_column(String(64), index=True)
    implementation_name: Mapped[str | None] = mapped_column(String(128), index=True)
    bot_id: Mapped[str | None] = mapped_column(String(128), index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), index=True)
    command_key: Mapped[str | None] = mapped_column(String(128), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    result: Mapped[str] = mapped_column(String(64), index=True)
    group_id: Mapped[int | None] = mapped_column(Integer, index=True)
    grant_node_id: Mapped[int | None] = mapped_column(Integer, index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    exception_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )
