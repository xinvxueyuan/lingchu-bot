"""Persist MCP service principals and exact resource grants."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mssql import NVARCHAR as MSSQL_NVARCHAR
from sqlalchemy.dialects.mysql import DATETIME as MYSQL_DATETIME
from sqlalchemy.dialects.oracle import CLOB as ORACLE_CLOB, NUMBER as ORACLE_NUMBER

if TYPE_CHECKING:
    from collections.abc import Sequence

# Inlined copy of ``database._dialect_compat`` so this migration stays
# self-contained (alembic loads migrations as standalone modules without a
# parent package, so relative imports fail). Keep in sync with the source
# module if the cross-dialect variant strategy changes.
_MSSQL_NVARCHAR_MAX = 4000

CompatBoolean = sa.Boolean().with_variant(
    ORACLE_NUMBER(1, asdecimal=False),
    "oracle",
)
CompatDateTimeTZ = sa.DateTime(timezone=True).with_variant(
    MYSQL_DATETIME(fsp=6),
    "mysql",
    "mariadb",
)


def compat_string(length: int) -> Any:
    """Cross-dialect ``String(length)`` mirroring ``_dialect_compat.compat_string``."""
    base = sa.String(length)
    if length > _MSSQL_NVARCHAR_MAX:
        return base.with_variant(MSSQL_NVARCHAR(None), "mssql").with_variant(
            ORACLE_CLOB, "oracle"
        )
    return base


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
        sa.Column("principal_id", compat_string(64), nullable=False),
        # 256 chars fits OAuth issuer URLs while keeping the
        # (issuer, identity_kind, identity_value) unique index below
        # MySQL/MariaDB's 3072-byte limit (256+16+256 = 528 chars x 4 bytes
        # utf8mb4 = 2112 bytes).
        sa.Column("issuer", compat_string(256), nullable=False),
        sa.Column("identity_kind", compat_string(16), nullable=False),
        sa.Column("identity_value", compat_string(256), nullable=False),
        sa.Column("display_name", compat_string(128), nullable=False),
        sa.Column("enabled", CompatBoolean, nullable=False),
        sa.Column("created_at", CompatDateTimeTZ, nullable=False),
        sa.Column("updated_at", CompatDateTimeTZ, nullable=False),
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
        info={"bind_key": "nonebot_plugin_lingchu_bot"},
    )
    op.create_index(
        op.f("ix_lingchu_mcp_service_principals_issuer"),
        "lingchu_mcp_service_principals",
        ["issuer"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lingchu_mcp_service_principals_identity_kind"),
        "lingchu_mcp_service_principals",
        ["identity_kind"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lingchu_mcp_service_principals_identity_value"),
        "lingchu_mcp_service_principals",
        ["identity_value"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lingchu_mcp_service_principals_enabled"),
        "lingchu_mcp_service_principals",
        ["enabled"],
        unique=False,
    )
    op.create_table(
        "lingchu_mcp_resource_grants",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("grant_id", compat_string(64), nullable=False),
        sa.Column("principal_id", compat_string(64), nullable=False),
        sa.Column("platform_id", compat_string(64), nullable=False),
        sa.Column("adapter_id", compat_string(64), nullable=False),
        sa.Column("protocol_id", compat_string(64), nullable=False),
        sa.Column("bot_id", compat_string(128), nullable=False),
        sa.Column("conversation_type", compat_string(32), nullable=False),
        sa.Column("conversation_id", compat_string(128), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("revoked_at", CompatDateTimeTZ, nullable=True),
        sa.Column("created_at", CompatDateTimeTZ, nullable=False),
        sa.Column("updated_at", CompatDateTimeTZ, nullable=False),
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
        info={"bind_key": "nonebot_plugin_lingchu_bot"},
    )
    op.create_index(
        op.f("ix_lingchu_mcp_resource_grants_principal_id"),
        "lingchu_mcp_resource_grants",
        ["principal_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lingchu_mcp_resource_grants_platform_id"),
        "lingchu_mcp_resource_grants",
        ["platform_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lingchu_mcp_resource_grants_adapter_id"),
        "lingchu_mcp_resource_grants",
        ["adapter_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lingchu_mcp_resource_grants_protocol_id"),
        "lingchu_mcp_resource_grants",
        ["protocol_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lingchu_mcp_resource_grants_bot_id"),
        "lingchu_mcp_resource_grants",
        ["bot_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lingchu_mcp_resource_grants_conversation_type"),
        "lingchu_mcp_resource_grants",
        ["conversation_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lingchu_mcp_resource_grants_conversation_id"),
        "lingchu_mcp_resource_grants",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_lingchu_mcp_resource_grants_revoked_at"),
        "lingchu_mcp_resource_grants",
        ["revoked_at"],
        unique=False,
    )


def downgrade(name: str = "") -> None:
    if name:
        return
    op.drop_index(
        op.f("ix_lingchu_mcp_resource_grants_revoked_at"),
        table_name="lingchu_mcp_resource_grants",
    )
    op.drop_index(
        op.f("ix_lingchu_mcp_resource_grants_conversation_id"),
        table_name="lingchu_mcp_resource_grants",
    )
    op.drop_index(
        op.f("ix_lingchu_mcp_resource_grants_conversation_type"),
        table_name="lingchu_mcp_resource_grants",
    )
    op.drop_index(
        op.f("ix_lingchu_mcp_resource_grants_bot_id"),
        table_name="lingchu_mcp_resource_grants",
    )
    op.drop_index(
        op.f("ix_lingchu_mcp_resource_grants_protocol_id"),
        table_name="lingchu_mcp_resource_grants",
    )
    op.drop_index(
        op.f("ix_lingchu_mcp_resource_grants_adapter_id"),
        table_name="lingchu_mcp_resource_grants",
    )
    op.drop_index(
        op.f("ix_lingchu_mcp_resource_grants_platform_id"),
        table_name="lingchu_mcp_resource_grants",
    )
    op.drop_index(
        op.f("ix_lingchu_mcp_resource_grants_principal_id"),
        table_name="lingchu_mcp_resource_grants",
    )
    op.drop_table("lingchu_mcp_resource_grants")
    op.drop_index(
        op.f("ix_lingchu_mcp_service_principals_enabled"),
        table_name="lingchu_mcp_service_principals",
    )
    op.drop_index(
        op.f("ix_lingchu_mcp_service_principals_identity_value"),
        table_name="lingchu_mcp_service_principals",
    )
    op.drop_index(
        op.f("ix_lingchu_mcp_service_principals_identity_kind"),
        table_name="lingchu_mcp_service_principals",
    )
    op.drop_index(
        op.f("ix_lingchu_mcp_service_principals_issuer"),
        table_name="lingchu_mcp_service_principals",
    )
    op.drop_table("lingchu_mcp_service_principals")
