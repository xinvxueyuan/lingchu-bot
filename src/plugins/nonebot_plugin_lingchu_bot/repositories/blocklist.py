"""Repository helpers for platform user blocklists."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import or_

from ..database.models import BlocklistEntry
from ..database.orm_crud import delete, get_one, upsert

BlockScope = Literal["group", "global"]

GLOBAL_SCOPE_KEY = "*"


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


async def upsert_block(  # noqa: PLR0913
    *,
    platform_id: str,
    adapter_id: str,
    protocol_id: str | None = None,
    bot_id: str,
    scope: BlockScope,
    group_id: str | int | None,
    user_id: str | int,
    operator_id: str | int | None,
    reason: str | None,
    expires_at: datetime | None,
) -> BlocklistEntry:
    now = datetime.now(UTC)
    scope_key = scope_key_for(scope, group_id)
    values = {
        "platform_id": platform_id,
        "adapter_id": adapter_id,
        "protocol_id": protocol_id,
        "bot_id": bot_id,
        "scope": scope,
        "scope_key": scope_key,
        "group_id": None if scope == "global" else str(group_id),
        "user_id": str(user_id),
        "operator_id": None if operator_id is None else str(operator_id),
        "reason": reason,
        "expires_at": expires_at,
        "created_at": now,
        "updated_at": now,
    }
    return await upsert(
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
            "protocol_id": protocol_id,
            "operator_id": values["operator_id"],
            "reason": reason,
            "expires_at": expires_at,
            "updated_at": now,
        },
    )


async def remove_block(  # noqa: PLR0913
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
    return await delete(BlocklistEntry, filters)


async def clear_blocklist(  # noqa: PLR0913
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
    return await delete(BlocklistEntry, filters)


async def find_active_block(  # noqa: PLR0913
    *,
    platform_id: str,
    adapter_id: str,
    protocol_id: str | None = None,
    bot_id: str,
    group_id: str | int,
    user_id: str | int,
) -> BlocklistEntry | None:
    global_entry = await _find_active_block_for_scope(
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
        platform_id=platform_id,
        adapter_id=adapter_id,
        protocol_id=protocol_id,
        bot_id=bot_id,
        scope="group",
        group_id=group_id,
        user_id=user_id,
    )


async def _find_active_block_for_scope(  # noqa: PLR0913
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
    entry = await get_one(BlocklistEntry, filters)
    if entry is None:
        return None
    if entry.expires_at is None:
        return entry
    if entry.expires_at > datetime.now(UTC):
        return entry
    await delete(BlocklistEntry, filters)
    return None


async def cleanup_expired_blocks() -> tuple[int, bool]:
    now = datetime.now(UTC)
    return await delete(
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
