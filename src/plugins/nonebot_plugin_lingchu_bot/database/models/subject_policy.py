"""Subject policy ORM model for blocked and protected platform users."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from nonebot import require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import Model
from sqlalchemy import Identity, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .._dialect_compat import CompatDateTimeTZ, CompatText, compat_string
from .message import utc_now


class SubjectPolicyEntry(Model):
    """Stored user policy such as blocked or protected in a scope."""

    __tablename__ = "lingchu_subject_policy_entries"
    __table_args__ = (
        UniqueConstraint(
            "policy_type",
            "platform_id",
            "adapter_id",
            "protocol_id",
            "bot_id",
            "scope",
            "scope_key",
            "user_id",
            name="uq_lingchu_subject_policy_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    policy_type: Mapped[str] = mapped_column(compat_string(32), index=True)
    platform_id: Mapped[str] = mapped_column(compat_string(64), index=True)
    adapter_id: Mapped[str] = mapped_column(compat_string(64), index=True)
    protocol_id: Mapped[str | None] = mapped_column(compat_string(64), index=True)
    bot_id: Mapped[str] = mapped_column(compat_string(128), index=True)
    scope: Mapped[str] = mapped_column(compat_string(32), index=True)
    scope_key: Mapped[str] = mapped_column(compat_string(128), index=True)
    group_id: Mapped[str | None] = mapped_column(compat_string(128), index=True)
    user_id: Mapped[str] = mapped_column(compat_string(128), index=True)
    operator_id: Mapped[str | None] = mapped_column(compat_string(128), index=True)
    reason: Mapped[str | None] = mapped_column(CompatText)
    expires_at: Mapped[datetime | None] = mapped_column(
        CompatDateTimeTZ,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        CompatDateTimeTZ,
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        CompatDateTimeTZ,
        default=utc_now,
        onupdate=utc_now,
        index=True,
    )
