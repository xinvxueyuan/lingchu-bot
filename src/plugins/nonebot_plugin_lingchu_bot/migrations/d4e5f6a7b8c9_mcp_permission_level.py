"""add MCP permission level to identity groups

Revision ID: d4e5f6a7b8c9
Revises: cf2c06d51a17
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op
import sqlalchemy as sa

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "cf2c06d51a17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = "") -> None:
    if name:
        return
    op.add_column(
        "lingchu_platform_identity_groups",
        sa.Column("mcp_permission_level", sa.String(length=16), nullable=True),
    )


def downgrade(name: str = "") -> None:
    if name:
        return
    op.drop_column("lingchu_platform_identity_groups", "mcp_permission_level")
