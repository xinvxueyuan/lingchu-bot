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


def upgrade(name: str = "") -> None:
    if name:
        return

    with op.batch_alter_table(
        "lingchu_blocklist_entries",
        recreate="always",
    ) as batch_op:
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

    with op.batch_alter_table(
        "lingchu_blocklist_entries",
        recreate="always",
    ) as batch_op:
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
