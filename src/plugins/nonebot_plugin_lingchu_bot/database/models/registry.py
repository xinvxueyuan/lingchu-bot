"""Platform, adapter and protocol implementation registry ORM models."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from nonebot import require

require("nonebot_plugin_orm")
from nonebot_plugin_orm import Model
from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .message import utc_now


class Platform(Model):
    """Platform registry entry seeded from registry.py."""

    __tablename__ = "lingchu_platforms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(64))
    capabilities: Mapped[str] = mapped_column(Text)  # JSON array of capability strings
    implemented: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        index=True,
    )


class Adapter(Model):
    """Adapter registry entry seeded from registry.py."""

    __tablename__ = "lingchu_adapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    adapter_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    platform_id: Mapped[str] = mapped_column(String(64), index=True)
    display_name: Mapped[str] = mapped_column(String(64))
    nonebot_adapter_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
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
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    protocol_id: Mapped[str] = mapped_column(String(64), index=True)
    adapter_id: Mapped[str] = mapped_column(String(64), index=True)
    display_name: Mapped[str] = mapped_column(String(64))
    module_path: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        index=True,
    )
