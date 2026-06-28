"""permissions schema

迁移 ID: a1b2c3d4e5f6
父迁移: 30f5a01259cd
创建时间: 2026-06-19 16:30:00

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "30f5a01259cd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = "") -> None:
    if name:
        return

    op.create_table(
        "lingchu_identity_users",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("uid", sa.String(length=64), nullable=False),
        sa.Column("nickname", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lingchu_identity_users")),
        sa.UniqueConstraint("uid", name=op.f("uq_lingchu_identity_users_uid")),
        info={"bind_key": "nonebot_plugin_lingchu_bot"},
    )
    op.create_index(
        op.f("ix_lingchu_identity_users_created_at"),
        "lingchu_identity_users",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lingchu_identity_users_updated_at"),
        "lingchu_identity_users",
        ["updated_at"],
        unique=False,
    )

    op.create_table(
        "lingchu_platform_accounts",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("uid", sa.String(length=64), nullable=False),
        sa.Column("platform_id", sa.String(length=64), nullable=False),
        sa.Column("account_id", sa.String(length=128), nullable=False),
        sa.Column("account_type", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lingchu_platform_accounts")),
        sa.UniqueConstraint(
            "platform_id",
            "account_id",
            name="uq_lingchu_platform_account_identity",
        ),
        info={"bind_key": "nonebot_plugin_lingchu_bot"},
    )
    for column in (
        "uid",
        "platform_id",
        "account_id",
        "account_type",
        "created_at",
        "updated_at",
    ):
        op.create_index(
            op.f(f"ix_lingchu_platform_accounts_{column}"),
            "lingchu_platform_accounts",
            [column],
            unique=False,
        )

    op.create_table(
        "lingchu_platform_identity_groups",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("group_id", sa.String(length=128), nullable=False),
        sa.Column("platform_id", sa.String(length=64), nullable=False),
        sa.Column("parent_group_id", sa.String(length=128), nullable=True),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("builtin", sa.Boolean(), nullable=False),
        sa.Column("managed_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "id",
            name=op.f("pk_lingchu_platform_identity_groups"),
        ),
        sa.UniqueConstraint(
            "group_id",
            name=op.f("uq_lingchu_platform_identity_groups_group_id"),
        ),
        info={"bind_key": "nonebot_plugin_lingchu_bot"},
    )
    for column in (
        "platform_id",
        "parent_group_id",
        "builtin",
        "managed_by",
        "created_at",
        "updated_at",
    ):
        op.create_index(
            op.f(f"ix_lingchu_platform_identity_groups_{column}"),
            "lingchu_platform_identity_groups",
            [column],
            unique=False,
        )

    op.create_table(
        "lingchu_identity_memberships",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("uid", sa.String(length=64), nullable=False),
        sa.Column("group_id", sa.String(length=128), nullable=False),
        sa.Column("scope_type", sa.String(length=64), nullable=False),
        sa.Column("scope_id", sa.String(length=128), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lingchu_identity_memberships")),
        sa.UniqueConstraint(
            "uid",
            "group_id",
            "scope_type",
            "scope_id",
            name="uq_lingchu_identity_membership_identity",
        ),
        info={"bind_key": "nonebot_plugin_lingchu_bot"},
    )
    for column in (
        "uid",
        "group_id",
        "scope_type",
        "scope_id",
        "source",
        "created_at",
        "updated_at",
    ):
        op.create_index(
            op.f(f"ix_lingchu_identity_memberships_{column}"),
            "lingchu_identity_memberships",
            [column],
            unique=False,
        )

    op.create_table(
        "lingchu_permission_grants",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("group_id", sa.String(length=128), nullable=False),
        sa.Column("command_key", sa.String(length=128), nullable=False),
        sa.Column("effect", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lingchu_permission_grants")),
        sa.UniqueConstraint(
            "group_id",
            "command_key",
            name="uq_lingchu_permission_grant_identity",
        ),
        info={"bind_key": "nonebot_plugin_lingchu_bot"},
    )
    for column in (
        "group_id",
        "command_key",
        "effect",
        "created_at",
        "updated_at",
    ):
        op.create_index(
            op.f(f"ix_lingchu_permission_grants_{column}"),
            "lingchu_permission_grants",
            [column],
            unique=False,
        )


def downgrade(name: str = "") -> None:
    if name:
        return

    for column in (
        "updated_at",
        "created_at",
        "effect",
        "command_key",
        "group_id",
    ):
        op.drop_index(
            op.f(f"ix_lingchu_permission_grants_{column}"),
            table_name="lingchu_permission_grants",
        )
    op.drop_table("lingchu_permission_grants")

    for column in (
        "updated_at",
        "created_at",
        "source",
        "scope_id",
        "scope_type",
        "group_id",
        "uid",
    ):
        op.drop_index(
            op.f(f"ix_lingchu_identity_memberships_{column}"),
            table_name="lingchu_identity_memberships",
        )
    op.drop_table("lingchu_identity_memberships")

    for column in (
        "updated_at",
        "created_at",
        "managed_by",
        "builtin",
        "parent_group_id",
        "platform_id",
    ):
        op.drop_index(
            op.f(f"ix_lingchu_platform_identity_groups_{column}"),
            table_name="lingchu_platform_identity_groups",
        )
    op.drop_table("lingchu_platform_identity_groups")

    for column in (
        "updated_at",
        "created_at",
        "account_type",
        "account_id",
        "platform_id",
        "uid",
    ):
        op.drop_index(
            op.f(f"ix_lingchu_platform_accounts_{column}"),
            table_name="lingchu_platform_accounts",
        )
    op.drop_table("lingchu_platform_accounts")

    op.drop_index(
        op.f("ix_lingchu_identity_users_updated_at"),
        table_name="lingchu_identity_users",
    )
    op.drop_index(
        op.f("ix_lingchu_identity_users_created_at"),
        table_name="lingchu_identity_users",
    )
    op.drop_table("lingchu_identity_users")
