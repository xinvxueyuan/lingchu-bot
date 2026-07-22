"""Platform, adapter and protocol implementation registry ORM models."""

from __future__ import annotations

from datetime import datetime

from nonebot import require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import Model
from sqlalchemy import Identity, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .._dialect_compat import CompatBoolean, CompatDateTimeTZ, CompatText, compat_string
from .message import utc_now


class Platform(Model):
    """Platform registry entry seeded from registry.py."""

    __tablename__ = "lingchu_platforms"
    __table_args__ = ({"extend_existing": True},)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    platform_id: Mapped[str] = mapped_column(compat_string(64), unique=True)
    display_name: Mapped[str] = mapped_column(compat_string(64))
    # JSON array of capability strings.
    capabilities: Mapped[str] = mapped_column(CompatText)
    implemented: Mapped[bool] = mapped_column(CompatBoolean, default=True)
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


class Adapter(Model):
    """Adapter registry entry seeded from registry.py."""

    __tablename__ = "lingchu_adapters"
    __table_args__ = ({"extend_existing": True},)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    adapter_id: Mapped[str] = mapped_column(compat_string(64), unique=True)
    platform_id: Mapped[str] = mapped_column(compat_string(64), index=True)
    display_name: Mapped[str] = mapped_column(compat_string(64))
    nonebot_adapter_id: Mapped[str] = mapped_column(compat_string(64))
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


class ProtocolImplementation(Model):
    """Protocol implementation registry entry seeded from adapter modules."""

    __tablename__ = "lingchu_protocol_implementations"
    __table_args__ = (
        UniqueConstraint(
            "adapter_id",
            "protocol_id",
            name="uq_lingchu_protocol_implementation_identity",
        ),
        {"extend_existing": True},
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    protocol_id: Mapped[str] = mapped_column(compat_string(64), index=True)
    adapter_id: Mapped[str] = mapped_column(compat_string(64), index=True)
    display_name: Mapped[str] = mapped_column(compat_string(64))
    module_path: Mapped[str] = mapped_column(compat_string(256))
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
