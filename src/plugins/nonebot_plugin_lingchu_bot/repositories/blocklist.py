"""Repository helpers for platform user blocklists."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Literal

from sqlalchemy import or_

from ..database.models import BlocklistEntry
from ..database.orm_crud import delete, get_one, upsert

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session

BlockScope = Literal["group", "global"]

GLOBAL_SCOPE_KEY = "*"


@dataclass(frozen=True, slots=True)
class BlocklistUpsert:
    platform_id: str
    adapter_id: str
    bot_id: str
    scope: BlockScope
    group_id: str | int | None
    user_id: str | int
    operator_id: str | int | None
    reason: str | None
    expires_at: datetime | None
    protocol_id: str | None = None


def scope_key_for(scope: BlockScope, group_id: str | int | None = None) -> str:
    if scope == "global":
        return GLOBAL_SCOPE_KEY
    if group_id is None:
        msg = "group_id is required for group blocklist scope"
        raise ValueError(msg)
    return str(group_id)


def expires_at_from_duration(duration: int | None) -> datetime | None:
    if duration is None:
        return None
    if duration <= 0:
        return None
    return datetime.now(UTC) + timedelta(seconds=duration)


async def upsert_block(
    session: AsyncSession | async_scoped_session,
    request: BlocklistUpsert,
) -> BlocklistEntry:
    now = datetime.now(UTC)
    scope_key = scope_key_for(request.scope, request.group_id)
    values = {
        "platform_id": request.platform_id,
        "adapter_id": request.adapter_id,
        "protocol_id": request.protocol_id,
        "bot_id": request.bot_id,
        "scope": request.scope,
        "scope_key": scope_key,
        "group_id": None if request.scope == "global" else str(request.group_id),
        "user_id": str(request.user_id),
        "operator_id": None
        if request.operator_id is None
        else str(request.operator_id),
        "reason": request.reason,
        "expires_at": request.expires_at,
        "created_at": now,
        "updated_at": now,
    }
    entry = await upsert(
        session,
        BlocklistEntry,
        values,
        conflict_fields=[
            "platform_id",
            "adapter_id",
            "protocol_id",
            "bot_id",
            "scope",
            "scope_key",
            "user_id",
        ],
        update_values={
            "protocol_id": request.protocol_id,
            "operator_id": values["operator_id"],
            "reason": request.reason,
            "expires_at": request.expires_at,
            "updated_at": now,
        },
    )
    await _sync_blocked_policy_upsert(session, request)
    return entry


async def remove_block(
    session: AsyncSession | async_scoped_session,
    *,
    platform_id: str,
    adapter_id: str,
    protocol_id: str | None = None,
    bot_id: str,
    scope: BlockScope,
    group_id: str | int | None,
    user_id: str | int,
) -> tuple[int, bool]:
    filters = {
        "platform_id": platform_id,
        "adapter_id": adapter_id,
        "bot_id": bot_id,
        "scope": scope,
        "scope_key": scope_key_for(scope, group_id),
        "user_id": str(user_id),
    }
    if protocol_id is not None:
        filters["protocol_id"] = protocol_id
    result = await delete(session, BlocklistEntry, filters)
    await _sync_blocked_policy_remove(
        session,
        platform_id=platform_id,
        adapter_id=adapter_id,
        protocol_id=protocol_id,
        bot_id=bot_id,
        scope=scope,
        group_id=group_id,
        user_id=user_id,
    )
    return result


async def clear_blocklist(
    session: AsyncSession | async_scoped_session,
    *,
    platform_id: str,
    adapter_id: str,
    protocol_id: str | None = None,
    bot_id: str,
    scope: BlockScope,
    group_id: str | int | None,
) -> tuple[int, bool]:
    filters = {
        "platform_id": platform_id,
        "adapter_id": adapter_id,
        "bot_id": bot_id,
        "scope": scope,
        "scope_key": scope_key_for(scope, group_id),
    }
    if protocol_id is not None:
        filters["protocol_id"] = protocol_id
    result = await delete(session, BlocklistEntry, filters)
    await _sync_blocked_policy_clear(
        session,
        platform_id=platform_id,
        adapter_id=adapter_id,
        protocol_id=protocol_id,
        bot_id=bot_id,
        scope=scope,
        group_id=group_id,
    )
    return result


async def find_active_block(
    session: AsyncSession | async_scoped_session,
    *,
    platform_id: str,
    adapter_id: str,
    protocol_id: str | None = None,
    bot_id: str,
    group_id: str | int,
    user_id: str | int,
) -> BlocklistEntry | None:
    global_entry = await _find_active_block_for_scope(
        session,
        platform_id=platform_id,
        adapter_id=adapter_id,
        protocol_id=protocol_id,
        bot_id=bot_id,
        scope="global",
        group_id=None,
        user_id=user_id,
    )
    if global_entry is not None:
        return global_entry
    return await _find_active_block_for_scope(
        session,
        platform_id=platform_id,
        adapter_id=adapter_id,
        protocol_id=protocol_id,
        bot_id=bot_id,
        scope="group",
        group_id=group_id,
        user_id=user_id,
    )


async def _find_active_block_for_scope(
    session: AsyncSession | async_scoped_session,
    *,
    platform_id: str,
    adapter_id: str,
    protocol_id: str | None = None,
    bot_id: str,
    scope: BlockScope,
    group_id: str | int | None,
    user_id: str | int,
) -> BlocklistEntry | None:
    filters = {
        "platform_id": platform_id,
        "adapter_id": adapter_id,
        "bot_id": bot_id,
        "scope": scope,
        "scope_key": scope_key_for(scope, group_id),
        "user_id": str(user_id),
    }
    if protocol_id is not None:
        filters["protocol_id"] = protocol_id
    entry = await get_one(session, BlocklistEntry, filters)
    if entry is None:
        return None
    if entry.expires_at is None:
        return entry
    if entry.expires_at > datetime.now(UTC):
        return entry
    await delete(session, BlocklistEntry, filters)
    return None


async def cleanup_expired_blocks(
    session: AsyncSession | async_scoped_session,
) -> tuple[int, bool]:
    now = datetime.now(UTC)
    return await delete(
        session,
        BlocklistEntry,
        {},
        conditions=[
            BlocklistEntry.expires_at.is_not(None),
            BlocklistEntry.expires_at <= now,
        ],
    )


def active_block_condition() -> object:
    """Return the SQL condition used by callers that need active entries."""
    now = datetime.now(UTC)
    return or_(BlocklistEntry.expires_at.is_(None), BlocklistEntry.expires_at > now)


async def _sync_blocked_policy_upsert(
    session: AsyncSession | async_scoped_session,
    request: BlocklistUpsert,
) -> None:
    from ..permissions.subject_policy import SubjectPolicyUpsert, upsert_subject_policy

    await upsert_subject_policy(
        session,
        SubjectPolicyUpsert(
            policy_type="blocked",
            platform_id=request.platform_id,
            adapter_id=request.adapter_id,
            protocol_id=request.protocol_id,
            bot_id=request.bot_id,
            scope=request.scope,
            group_id=request.group_id,
            user_id=request.user_id,
            operator_id=request.operator_id,
            reason=request.reason,
            expires_at=request.expires_at,
        ),
    )


async def _sync_blocked_policy_remove(
    session: AsyncSession | async_scoped_session,
    *,
    platform_id: str,
    adapter_id: str,
    protocol_id: str | None,
    bot_id: str,
    scope: BlockScope,
    group_id: str | int | None,
    user_id: str | int,
) -> None:
    from ..permissions.subject_policy import remove_subject_policy

    await remove_subject_policy(
        session,
        policy_type="blocked",
        platform_id=platform_id,
        adapter_id=adapter_id,
        protocol_id=protocol_id,
        bot_id=bot_id,
        scope=scope,
        group_id=group_id,
        user_id=user_id,
    )


async def _sync_blocked_policy_clear(
    session: AsyncSession | async_scoped_session,
    *,
    platform_id: str,
    adapter_id: str,
    protocol_id: str | None,
    bot_id: str,
    scope: BlockScope,
    group_id: str | int | None,
) -> None:
    from ..permissions.subject_policy import clear_subject_policy

    await clear_subject_policy(
        session,
        policy_type="blocked",
        platform_id=platform_id,
        adapter_id=adapter_id,
        protocol_id=protocol_id,
        bot_id=bot_id,
        scope=scope,
        group_id=group_id,
    )
