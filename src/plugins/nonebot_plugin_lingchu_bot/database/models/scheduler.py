"""Persistent scheduler job ORM model."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from nonebot import require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import Model
from sqlalchemy import Identity, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .._dialect_compat import CompatBoolean, CompatDateTimeTZ, CompatText, compat_string
from .message import utc_now


class ScheduledJob(Model):
    """Persistent scheduled job definition."""

    __tablename__ = "lingchu_scheduled_jobs"
    __table_args__ = (
        UniqueConstraint(
            "job_id",
            name="uq_lingchu_scheduled_jobs_job_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    job_id: Mapped[str] = mapped_column(compat_string(128), index=True)
    handler_key: Mapped[str] = mapped_column(compat_string(128), index=True)
    trigger_type: Mapped[str] = mapped_column(compat_string(32))
    trigger_kwargs: Mapped[str] = mapped_column(CompatText)
    args: Mapped[str] = mapped_column(CompatText, default="[]")
    kwargs: Mapped[str] = mapped_column(CompatText, default="{}")
    enabled: Mapped[bool] = mapped_column(CompatBoolean, default=True, index=True)
    coalesce: Mapped[bool] = mapped_column(CompatBoolean, default=True)
    max_instances: Mapped[int] = mapped_column(Integer, default=1)
    misfire_grace_time: Mapped[int | None] = mapped_column(Integer)
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
