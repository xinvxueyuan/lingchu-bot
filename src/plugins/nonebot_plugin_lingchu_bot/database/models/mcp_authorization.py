from __future__ import annotations

from datetime import datetime

from nonebot import require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import Model
from sqlalchemy import CheckConstraint, ForeignKey, Identity, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .._dialect_compat import CompatBoolean, CompatDateTimeTZ, compat_string
from .message import utc_now


class MCPServicePrincipal(Model):
    """Stable mapping from an OAuth issuer identity to a service principal."""

    __tablename__ = "lingchu_mcp_service_principals"
    __table_args__ = (
        CheckConstraint(
            "identity_kind IN ('subject', 'client_id')",
            name="ck_lingchu_mcp_principal_identity_kind",
        ),
        UniqueConstraint(
            "issuer",
            "identity_kind",
            "identity_value",
            name="uq_lingchu_mcp_principal_oauth_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    principal_id: Mapped[str] = mapped_column(compat_string(64), unique=True)
    issuer: Mapped[str] = mapped_column(compat_string(512), index=True)
    identity_kind: Mapped[str] = mapped_column(compat_string(16), index=True)
    identity_value: Mapped[str] = mapped_column(compat_string(256), index=True)
    display_name: Mapped[str] = mapped_column(compat_string(128))
    enabled: Mapped[bool] = mapped_column(CompatBoolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(CompatDateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        CompatDateTimeTZ, default=utc_now, onupdate=utc_now
    )


class MCPResourceGrant(Model):
    """Revocable authorization for one exact bot conversation resource."""

    __tablename__ = "lingchu_mcp_resource_grants"
    __table_args__ = (
        UniqueConstraint(
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

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    grant_id: Mapped[str] = mapped_column(compat_string(64), unique=True)
    principal_id: Mapped[str] = mapped_column(
        compat_string(64),
        ForeignKey("lingchu_mcp_service_principals.principal_id", ondelete="CASCADE"),
        index=True,
    )
    platform_id: Mapped[str] = mapped_column(compat_string(64), index=True)
    adapter_id: Mapped[str] = mapped_column(compat_string(64), index=True)
    protocol_id: Mapped[str] = mapped_column(compat_string(64), index=True)
    bot_id: Mapped[str] = mapped_column(compat_string(128), index=True)
    conversation_type: Mapped[str] = mapped_column(compat_string(32), index=True)
    conversation_id: Mapped[str] = mapped_column(compat_string(128), index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    revoked_at: Mapped[datetime | None] = mapped_column(CompatDateTimeTZ, index=True)
    created_at: Mapped[datetime] = mapped_column(CompatDateTimeTZ, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        CompatDateTimeTZ, default=utc_now, onupdate=utc_now
    )
