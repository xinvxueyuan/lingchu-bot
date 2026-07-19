"""Backfill the generic OneBot V11 message protocol identity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op
import sqlalchemy as sa

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MESSAGE_TABLES = (
    "lingchu_message_records",
    "lingchu_qq_onebot_v11_nonebot_event_records",
)


def upgrade(name: str = "") -> None:
    """Replace only generic QQ OneBot V11 NULL protocol identities."""
    if name:
        return
    for table_name in _MESSAGE_TABLES:
        table = sa.table(
            table_name,
            sa.column("platform_id", sa.String(length=64)),
            sa.column("adapter_id", sa.String(length=64)),
            sa.column("protocol_id", sa.String(length=64)),
        )
        op.execute(
            table
            .update()
            .where(table.c.platform_id == "qq")
            .where(table.c.adapter_id == "~onebot.v11")
            .where(table.c.protocol_id.is_(None))
            .values(protocol_id="default")
        )


def downgrade(name: str = "") -> None:
    """Keep backfilled identities because their previous NULL origin is unknowable."""
    _ = name
