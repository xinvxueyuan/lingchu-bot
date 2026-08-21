"""Normalize protocol identity sentinels before enforcing uniqueness."""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op
import sqlalchemy as sa

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "g7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "lingchu_message_records",
    "lingchu_blocklist_entries",
    "lingchu_subject_policy_entries",
)


def upgrade(name: str = "") -> None:
    """Backfill legacy NULL values and make protocol identity mandatory."""
    if name:
        return
    for table_name in _TABLES:
        table = sa.table(
            table_name,
            sa.column("protocol_id", sa.String(length=64)),
        )
        op.execute(
            table
            .update()
            .where(table.c.protocol_id.is_(None))
            .values(protocol_id="unknown")
        )
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                "protocol_id",
                existing_type=sa.String(length=64),
                nullable=False,
            )


def downgrade(name: str = "") -> None:
    """Restore nullable protocol identities for rollback compatibility."""
    if name:
        return
    for table_name in _TABLES:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column(
                "protocol_id",
                existing_type=sa.String(length=64),
                nullable=True,
            )
