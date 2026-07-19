"""Persist MCP service principals and exact resource grants."""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op
import sqlalchemy as sa

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade(name: str = "") -> None:
    if name:
        return
    op.create_table(
        "lingchu_mcp_service_principals",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("principal_id", sa.String(length=64), nullable=False),
        sa.Column("issuer", sa.String(length=512), nullable=False),
        sa.Column("identity_kind", sa.String(length=16), nullable=False),
        sa.Column("identity_value", sa.String(length=256), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "identity_kind IN ('subject', 'client_id')",
            name="ck_lingchu_mcp_principal_identity_kind",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lingchu_mcp_service_principals")),
        sa.UniqueConstraint(
            "principal_id", name=op.f("uq_lingchu_mcp_service_principals_principal_id")
        ),
        sa.UniqueConstraint(
            "issuer",
            "identity_kind",
            "identity_value",
            name="uq_lingchu_mcp_principal_oauth_identity",
        ),
    )
    op.create_table(
        "lingchu_mcp_resource_grants",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("grant_id", sa.String(length=64), nullable=False),
        sa.Column("principal_id", sa.String(length=64), nullable=False),
        sa.Column("platform_id", sa.String(length=64), nullable=False),
        sa.Column("adapter_id", sa.String(length=64), nullable=False),
        sa.Column("protocol_id", sa.String(length=64), nullable=False),
        sa.Column("bot_id", sa.String(length=128), nullable=False),
        sa.Column("conversation_type", sa.String(length=32), nullable=False),
        sa.Column("conversation_id", sa.String(length=128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["principal_id"],
            ["lingchu_mcp_service_principals.principal_id"],
            ondelete="CASCADE",
            name=op.f(
                "fk_lingchu_mcp_resource_grants_principal_id_lingchu_mcp_service_principals"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lingchu_mcp_resource_grants")),
        sa.UniqueConstraint(
            "grant_id", name=op.f("uq_lingchu_mcp_resource_grants_grant_id")
        ),
        sa.UniqueConstraint(
            "principal_id",
            "platform_id",
            "adapter_id",
            "protocol_id",
            "bot_id",
            "conversation_type",
            "conversation_id",
            name="uq_lingchu_mcp_grant_exact_resource",
        ),
    )


def downgrade(name: str = "") -> None:
    if name:
        return
    op.drop_table("lingchu_mcp_resource_grants")
    op.drop_table("lingchu_mcp_service_principals")
