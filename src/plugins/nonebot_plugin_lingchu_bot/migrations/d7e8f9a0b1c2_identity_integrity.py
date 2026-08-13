"""Add identity ownership metadata, foreign keys and global scope IDs."""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op
import sqlalchemy as sa

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "d7e8f9a0b1c2"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_GLOBAL_SCOPE_ID_SENTINEL = "__lingchu_global_scope__"
_MANUAL_SOURCE = "manual"
_SUPERUSER_SOURCE = "superusers_config"
_PLATFORM_ACCOUNTS_TABLE = "lingchu_platform_accounts"
_MEMBERSHIP_TABLE = "lingchu_identity_memberships"


def _backfill_global_scope_ids() -> None:
    """Normalize NULL global scopes and remove duplicates before constraints."""
    bind = op.get_bind()
    table = sa.table(
        _MEMBERSHIP_TABLE,
        sa.column("id", sa.Integer()),
        sa.column("uid", sa.String(length=64)),
        sa.column("group_id", sa.String(length=128)),
        sa.column("scope_type", sa.String(length=64)),
        sa.column("scope_id", sa.String(length=128)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    scope_condition = sa.or_(
        table.c.scope_id.is_(None),
        table.c.scope_id == _GLOBAL_SCOPE_ID_SENTINEL,
    )
    rows = bind.execute(
        sa
        .select(
            table.c.id,
            table.c.uid,
            table.c.group_id,
            table.c.scope_type,
            table.c.scope_id,
        )
        .where(scope_condition)
        .order_by(
            table.c.uid,
            table.c.group_id,
            table.c.scope_type,
            table.c.updated_at.desc(),
            table.c.id.desc(),
        )
    ).mappings()

    seen: set[tuple[str, str, str]] = set()
    duplicate_ids: list[int] = []
    for row in rows:
        key = (row["uid"], row["group_id"], row["scope_type"])
        if key in seen:
            duplicate_ids.append(row["id"])
        else:
            seen.add(key)

    if duplicate_ids:
        bind.execute(table.delete().where(table.c.id.in_(duplicate_ids)))
    bind.execute(
        table
        .update()
        .where(table.c.scope_id.is_(None))
        .values(scope_id=_GLOBAL_SCOPE_ID_SENTINEL)
    )


def _add_platform_account_source() -> None:
    """Add ownership metadata and classify existing superuser bindings."""
    with op.batch_alter_table(_PLATFORM_ACCOUNTS_TABLE) as batch_op:
        batch_op.add_column(
            sa.Column(
                "source",
                sa.String(length=64),
                nullable=False,
                server_default=_MANUAL_SOURCE,
            )
        )
    op.create_index(
        op.f("ix_lingchu_platform_accounts_source"),
        _PLATFORM_ACCOUNTS_TABLE,
        ["source"],
        unique=False,
    )

    bind = op.get_bind()
    accounts = sa.table(
        _PLATFORM_ACCOUNTS_TABLE,
        sa.column("uid", sa.String(length=64)),
        sa.column("source", sa.String(length=64)),
    )
    memberships = sa.table(
        _MEMBERSHIP_TABLE,
        sa.column("uid", sa.String(length=64)),
        sa.column("group_id", sa.String(length=128)),
        sa.column("scope_type", sa.String(length=64)),
        sa.column("scope_id", sa.String(length=128)),
        sa.column("source", sa.String(length=64)),
    )
    superuser_uids = sa.select(memberships.c.uid).where(
        memberships.c.group_id == "system.superusers",
        memberships.c.scope_type == "global",
        memberships.c.scope_id == _GLOBAL_SCOPE_ID_SENTINEL,
        memberships.c.source == _SUPERUSER_SOURCE,
    )
    bind.execute(
        accounts
        .update()
        .where(
            accounts.c.uid.in_(superuser_uids),
            accounts.c.source == _MANUAL_SOURCE,
        )
        .values(source=_SUPERUSER_SOURCE)
    )


_FOREIGN_KEYS = (
    (
        "lingchu_platform_accounts",
        "fk_lingchu_platform_accounts_uid_identity_users",
        ["uid"],
        "lingchu_identity_users",
        ["uid"],
        "CASCADE",
    ),
    (
        "lingchu_platform_identity_groups",
        "fk_lingchu_identity_groups_parent",
        ["parent_group_id"],
        "lingchu_platform_identity_groups",
        ["group_id"],
        "SET NULL",
    ),
    (
        "lingchu_identity_memberships",
        "fk_lingchu_identity_memberships_uid_identity_users",
        ["uid"],
        "lingchu_identity_users",
        ["uid"],
        "CASCADE",
    ),
    (
        "lingchu_identity_memberships",
        "fk_lingchu_identity_memberships_group_id_identity_groups",
        ["group_id"],
        "lingchu_platform_identity_groups",
        ["group_id"],
        "CASCADE",
    ),
    (
        "lingchu_permission_grants",
        "fk_lingchu_permission_grants_group_id_identity_groups",
        ["group_id"],
        "lingchu_platform_identity_groups",
        ["group_id"],
        "CASCADE",
    ),
)


def upgrade(name: str = "") -> None:
    """Backfill global scopes and add identity referential integrity."""
    if name:
        return

    _backfill_global_scope_ids()
    _add_platform_account_source()
    for (
        table_name,
        constraint_name,
        local_cols,
        remote_table,
        remote_cols,
        ondelete,
    ) in _FOREIGN_KEYS:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.create_foreign_key(
                constraint_name,
                remote_table,
                local_cols,
                remote_cols,
                ondelete=ondelete,
            )


def downgrade(name: str = "") -> None:
    """Remove identity foreign keys and restore NULL global scopes."""
    if name:
        return

    bind = op.get_bind()
    table = sa.table(
        _MEMBERSHIP_TABLE,
        sa.column("scope_id", sa.String(length=128)),
    )
    bind.execute(
        table
        .update()
        .where(table.c.scope_id == _GLOBAL_SCOPE_ID_SENTINEL)
        .values(scope_id=None)
    )
    for table_name, constraint_name, *_ in reversed(_FOREIGN_KEYS):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_constraint(constraint_name, type_="foreignkey")
    op.drop_index(
        op.f("ix_lingchu_platform_accounts_source"),
        table_name=_PLATFORM_ACCOUNTS_TABLE,
    )
    with op.batch_alter_table(_PLATFORM_ACCOUNTS_TABLE) as batch_op:
        batch_op.drop_column("source")
