"""Identity, platform account, group membership and permission ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, override

from nonebot import require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import Model
from sqlalchemy import ForeignKey, Identity, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

from .._dialect_compat import CompatBoolean, CompatDateTimeTZ, compat_string
from .message import utc_now

if TYPE_CHECKING:
    from sqlalchemy.engine import Dialect

GLOBAL_SCOPE_ID_SENTINEL = "__lingchu_global_scope__"


class _ScopeIdType(TypeDecorator[str]):
    """Store an application-level ``None`` scope as a unique database value.

    SQL NULLs do not collide in composite unique constraints on the supported
    databases.  Keeping the public Python value as ``None`` while storing a
    reserved non-null sentinel lets the membership identity constraint remain
    conflict-safe without changing the repository API.
    """

    impl = compat_string(128)
    cache_ok = True
    should_evaluate_none = True

    @override
    def process_bind_param(self, value: str | None, dialect: Dialect) -> str:
        del dialect
        return GLOBAL_SCOPE_ID_SENTINEL if value is None else value

    @override
    def process_result_value(
        self,
        value: Any,
        dialect: Dialect,
    ) -> str | None:
        del dialect
        return None if value == GLOBAL_SCOPE_ID_SENTINEL else value


class IdentityUser(Model):
    """Lingchu-wide user identity used across platform accounts."""

    __tablename__ = "lingchu_identity_users"
    __table_args__ = ({"extend_existing": True},)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    uid: Mapped[str] = mapped_column(compat_string(64), unique=True)
    nickname: Mapped[str] = mapped_column(compat_string(128))
    created_at: Mapped[datetime] = mapped_column(
        CompatDateTimeTZ,
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        CompatDateTimeTZ,
        default=utc_now,
        onupdate=utc_now,
        index=True,
    )


class PlatformAccount(Model):
    """Binding between a Lingchu UID and one platform account.

    ``source`` identifies the subsystem that owns the binding.  Keeping the
    ownership on the row lets authoritative configuration syncs remove only
    their own stale bindings without touching manually managed identities.
    """

    __tablename__ = "lingchu_platform_accounts"
    __table_args__ = (
        UniqueConstraint(
            "platform_id",
            "account_id",
            name="uq_lingchu_platform_account_identity",
        ),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    uid: Mapped[str] = mapped_column(
        compat_string(64),
        ForeignKey(
            "lingchu_identity_users.uid",
            ondelete="CASCADE",
            name="fk_lingchu_platform_accounts_uid_identity_users",
        ),
        index=True,
    )
    platform_id: Mapped[str] = mapped_column(compat_string(64), index=True)
    account_id: Mapped[str] = mapped_column(compat_string(128), index=True)
    account_type: Mapped[str] = mapped_column(
        compat_string(64), default="user", index=True
    )
    display_name: Mapped[str | None] = mapped_column(compat_string(128))
    source: Mapped[str] = mapped_column(compat_string(64), default="manual", index=True)
    created_at: Mapped[datetime] = mapped_column(
        CompatDateTimeTZ,
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        CompatDateTimeTZ,
        default=utc_now,
        onupdate=utc_now,
        index=True,
    )


class PlatformIdentityGroup(Model):
    """Platform-scoped identity group, including builtin and custom groups."""

    __tablename__ = "lingchu_platform_identity_groups"
    __table_args__ = ({"extend_existing": True},)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    group_id: Mapped[str] = mapped_column(compat_string(128), unique=True)
    platform_id: Mapped[str] = mapped_column(compat_string(64), index=True)
    parent_group_id: Mapped[str | None] = mapped_column(
        compat_string(128),
        ForeignKey(
            "lingchu_platform_identity_groups.group_id",
            ondelete="SET NULL",
            name="fk_lingchu_identity_groups_parent",
        ),
        index=True,
    )
    display_name: Mapped[str] = mapped_column(compat_string(128))
    builtin: Mapped[bool] = mapped_column(CompatBoolean, default=False, index=True)
    managed_by: Mapped[str | None] = mapped_column(compat_string(64), index=True)
    created_at: Mapped[datetime] = mapped_column(
        CompatDateTimeTZ,
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        CompatDateTimeTZ,
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
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    uid: Mapped[str] = mapped_column(
        compat_string(64),
        ForeignKey(
            "lingchu_identity_users.uid",
            ondelete="CASCADE",
            name="fk_lingchu_identity_memberships_uid_identity_users",
        ),
        index=True,
    )
    group_id: Mapped[str] = mapped_column(
        compat_string(128),
        ForeignKey(
            "lingchu_platform_identity_groups.group_id",
            ondelete="CASCADE",
            name="fk_lingchu_identity_memberships_group_id_identity_groups",
        ),
        index=True,
    )
    scope_type: Mapped[str] = mapped_column(
        compat_string(64), default="global", index=True
    )
    scope_id: Mapped[str | None] = mapped_column(_ScopeIdType(), index=True)
    source: Mapped[str] = mapped_column(compat_string(64), default="manual", index=True)
    created_at: Mapped[datetime] = mapped_column(
        CompatDateTimeTZ,
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        CompatDateTimeTZ,
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
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    group_id: Mapped[str] = mapped_column(
        compat_string(128),
        ForeignKey(
            "lingchu_platform_identity_groups.group_id",
            ondelete="CASCADE",
            name="fk_lingchu_permission_grants_group_id_identity_groups",
        ),
        index=True,
    )
    command_key: Mapped[str] = mapped_column(compat_string(128), index=True)
    effect: Mapped[str] = mapped_column(compat_string(16), default="allow", index=True)
    created_at: Mapped[datetime] = mapped_column(
        CompatDateTimeTZ,
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        CompatDateTimeTZ,
        default=utc_now,
        onupdate=utc_now,
        index=True,
    )
