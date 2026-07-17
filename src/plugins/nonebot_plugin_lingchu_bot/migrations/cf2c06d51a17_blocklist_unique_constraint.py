"""blocklist unique constraint

迁移 ID: cf2c06d51a17
父迁移: c3d4e5f6a7b8
创建时间: 2026-07-04 01:56:06

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "cf2c06d51a17"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _mysql_drop_index(index_name: str, table_name: str) -> None:
    """MySQL/MariaDB 端把 unique constraint 视作 unique index。"""
    op.drop_index(index_name, table_name=table_name)


def _mysql_create_index(index_name: str, table_name: str, columns: list[str]) -> None:
    """MySQL/MariaDB 端以 unique index 形式重建唯一约束。"""
    op.create_index(
        index_name,
        table_name,
        columns,
        unique=True,
    )


def upgrade(name: str = "") -> None:
    if name:
        return

    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect in {"mysql", "mariadb"}:
        _mysql_drop_index(
            "uq_lingchu_blocklist_entry_identity",
            "lingchu_blocklist_entries",
        )
        _mysql_create_index(
            "uq_lingchu_blocklist_entry_identity",
            "lingchu_blocklist_entries",
            [
                "platform_id",
                "adapter_id",
                "bot_id",
                "scope",
                "scope_key",
                "user_id",
            ],
        )
        return

    with op.batch_alter_table("lingchu_blocklist_entries") as batch_op:
        batch_op.drop_constraint(
            "uq_lingchu_blocklist_entry_identity",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_lingchu_blocklist_entry_identity",
            ["platform_id", "adapter_id", "bot_id", "scope", "scope_key", "user_id"],
        )


def downgrade(name: str = "") -> None:
    if name:
        return

    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect in {"mysql", "mariadb"}:
        _mysql_drop_index(
            "uq_lingchu_blocklist_entry_identity",
            "lingchu_blocklist_entries",
        )
        _mysql_create_index(
            "uq_lingchu_blocklist_entry_identity",
            "lingchu_blocklist_entries",
            [
                "platform_id",
                "adapter_id",
                "protocol_id",
                "bot_id",
                "scope",
                "scope_key",
                "user_id",
            ],
        )
        return

    with op.batch_alter_table("lingchu_blocklist_entries") as batch_op:
        batch_op.drop_constraint(
            "uq_lingchu_blocklist_entry_identity",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_lingchu_blocklist_entry_identity",
            [
                "platform_id",
                "adapter_id",
                "protocol_id",
                "bot_id",
                "scope",
                "scope_key",
                "user_id",
            ],
        )
