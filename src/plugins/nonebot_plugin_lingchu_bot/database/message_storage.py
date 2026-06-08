"""Adapter-scoped SQLite storage for message and audit records."""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Final

from nonebot_plugin_localstore import get_plugin_data_dir
from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ..platforms import PlatformProfile, iter_platform_profiles
from .orm_crud import DatabaseError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

MESSAGE_STORE_DIRNAME: Final[str] = "message_store"
ADAPTER_DB_NAME_CACHE: dict[tuple[str, str], Path] = {}


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base class for adapter-scoped SQLAlchemy models."""


class MessageRecord(Base):
    """Real incoming message event stored in an adapter-specific database."""

    __tablename__ = "message_records"
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "adapter",
            "bot_id",
            "conversation_id",
            "message_id",
            name="uq_message_record_identity",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(64), index=True)
    adapter: Mapped[str] = mapped_column(String(64), index=True)
    bot_id: Mapped[str] = mapped_column(String(128), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(128), index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), index=True)
    message_id: Mapped[str | None] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    message_type: Mapped[str | None] = mapped_column(String(64), index=True)
    text_summary: Mapped[str | None] = mapped_column(Text)
    raw_message: Mapped[str | None] = mapped_column(Text)
    raw_event: Mapped[str | None] = mapped_column(Text)
    process_status: Mapped[str] = mapped_column(
        String(32),
        default="received",
        index=True,
    )
    exception_summary: Mapped[str | None] = mapped_column(Text)
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


class PlatformMessageRecord(Base):
    """Common projection for platform-level message queries."""

    __tablename__ = "platform_message_records"
    __table_args__ = (
        UniqueConstraint(
            "source_adapter_id",
            "source_record_id",
            name="uq_platform_message_record_source",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_adapter_id: Mapped[str] = mapped_column(String(64), index=True)
    source_record_id: Mapped[int] = mapped_column(Integer, index=True)
    platform: Mapped[str] = mapped_column(String(64), index=True)
    adapter: Mapped[str] = mapped_column(String(64), index=True)
    bot_id: Mapped[str] = mapped_column(String(128), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(128), index=True)
    user_id: Mapped[str | None] = mapped_column(String(128), index=True)
    message_id: Mapped[str | None] = mapped_column(String(128), index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    message_type: Mapped[str | None] = mapped_column(String(64), index=True)
    text_summary: Mapped[str | None] = mapped_column(Text)
    raw_message: Mapped[str | None] = mapped_column(Text)
    raw_event: Mapped[str | None] = mapped_column(Text)
    process_status: Mapped[str] = mapped_column(String(32), index=True)
    exception_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AuditRecord(Base):
    """Adapter-scoped audit event for API calls and bot lifecycle events."""

    __tablename__ = "audit_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(64), index=True)
    adapter: Mapped[str] = mapped_column(String(64), index=True)
    bot_id: Mapped[str] = mapped_column(String(128), index=True)
    audit_type: Mapped[str] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    data_summary: Mapped[str | None] = mapped_column(Text)
    result_summary: Mapped[str | None] = mapped_column(Text)
    exception_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        index=True,
    )


@dataclass(frozen=True, slots=True)
class StorageTarget:
    """Physical database locations for an adapter and its platform projection."""

    platform_id: str
    adapter_id: str
    adapter_db: Path
    compat_db: Path


@dataclass(slots=True)
class _EngineState:
    engine: AsyncEngine
    sessionmaker: async_sessionmaker[AsyncSession]
    initialized: bool = False


_ENGINES: dict[Path, _EngineState] = {}


def adapter_slug(adapter_id: str) -> str:
    """Return a filesystem-safe slug for a canonical adapter id."""
    slug = adapter_id.strip().lstrip("~")
    return re.sub(r"[^0-9A-Za-z]+", "_", slug).strip("_").lower() or "unknown"


def message_store_root() -> Path:
    """Return the root directory for adapter-scoped message databases."""
    return get_plugin_data_dir() / MESSAGE_STORE_DIRNAME


def storage_target(platform_id: str, adapter_id: str) -> StorageTarget:
    """Build deterministic database paths for an adapter."""
    platform_root = message_store_root() / platform_id
    adapter_db = platform_root / f"{adapter_slug(adapter_id)}.db"
    compat_db = platform_root / "compat.db"
    ADAPTER_DB_NAME_CACHE[(platform_id, adapter_id)] = adapter_db
    return StorageTarget(
        platform_id=platform_id,
        adapter_id=adapter_id,
        adapter_db=adapter_db,
        compat_db=compat_db,
    )


def iter_known_targets() -> tuple[StorageTarget, ...]:
    """Return storage targets for every registry-declared adapter."""
    return tuple(
        storage_target(profile.platform_id, adapter_id)
        for profile in iter_platform_profiles()
        for adapter_id in profile.nonebot_adapters
    )


def platform_for_adapter(adapter_id: str) -> str | None:
    """Return the platform id declared for a canonical adapter id."""
    return next(
        (
            profile.platform_id
            for profile in iter_platform_profiles()
            if adapter_id in profile.nonebot_adapters
        ),
        None,
    )


def adapters_for_platform(platform_id: str) -> tuple[str, ...]:
    """Return canonical adapter ids declared for a platform."""
    profile: PlatformProfile | None = next(
        (
            candidate
            for candidate in iter_platform_profiles()
            if candidate.platform_id == platform_id
        ),
        None,
    )
    return profile.nonebot_adapters if profile is not None else ()


async def close_engines() -> None:
    """Dispose cached async engines. Primarily useful for tests."""
    states = tuple(_ENGINES.values())
    _ENGINES.clear()
    for state in states:
        await state.engine.dispose()


def _engine_state(path: Path) -> _EngineState:
    resolved = path.resolve()
    if resolved in _ENGINES:
        return _ENGINES[resolved]
    resolved.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite+aiosqlite:///{resolved.as_posix()}"
    engine = create_async_engine(url)
    state = _EngineState(
        engine=engine,
        sessionmaker=async_sessionmaker(engine, expire_on_commit=False),
    )
    _ENGINES[resolved] = state
    return state


async def _initialize(path: Path) -> _EngineState:
    state = _engine_state(path)
    if state.initialized:
        return state
    try:
        async with state.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except SQLAlchemyError as exc:
        raise DatabaseError(str(exc)) from exc
    state.initialized = True
    return state


@asynccontextmanager
async def session_for(path: Path) -> AsyncIterator[AsyncSession]:
    """Yield an initialized async session for a message-store database."""
    state = await _initialize(path)
    async with state.sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as exc:
            await session.rollback()
            raise DatabaseError(str(exc)) from exc


def copy_message_fields(record: MessageRecord) -> dict[str, Any]:
    """Return the common projection fields for an adapter message record."""
    return {
        "platform": record.platform,
        "adapter": record.adapter,
        "bot_id": record.bot_id,
        "conversation_id": record.conversation_id,
        "user_id": record.user_id,
        "message_id": record.message_id,
        "event_type": record.event_type,
        "message_type": record.message_type,
        "text_summary": record.text_summary,
        "raw_message": record.raw_message,
        "raw_event": record.raw_event,
        "process_status": record.process_status,
        "exception_summary": record.exception_summary,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


async def cleanup_table(
    session: AsyncSession,
    model: type[MessageRecord | PlatformMessageRecord | AuditRecord],
    cutoff: datetime,
) -> int:
    """Delete model rows older than cutoff and return the known rowcount."""
    result = await session.execute(delete(model).where(model.created_at < cutoff))
    rowcount = getattr(result, "rowcount", 0)
    return 0 if rowcount is None or rowcount < 0 else rowcount


async def fetch_one_message(  # noqa: PLR0913
    session: AsyncSession,
    *,
    platform: str,
    adapter: str,
    bot_id: str,
    conversation_id: str | None,
    message_id: str,
) -> MessageRecord | None:
    """Fetch one adapter message by stable identity."""
    result = await session.execute(
        select(MessageRecord).where(
            MessageRecord.platform == platform,
            MessageRecord.adapter == adapter,
            MessageRecord.bot_id == bot_id,
            MessageRecord.conversation_id == conversation_id,
            MessageRecord.message_id == message_id,
        )
    )
    return result.scalar_one_or_none()
