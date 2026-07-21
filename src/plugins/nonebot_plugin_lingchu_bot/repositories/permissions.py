"""Repository helpers for the permission system."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from ..database.models import (
    IdentityMembership,
    IdentityUser,
    PermissionGrant,
    PlatformAccount,
    PlatformIdentityGroup,
)
from ..database.orm_crud import create, delete, get_one, list_items, update, upsert
from ..permissions.types import MCPPermissionLevel, PlatformIdentityGroupSeed

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session

SUPERUSERS_GROUP_ID = "system.superusers"
SUPERUSERS_PLATFORM_ID = "system"
SUPERUSER_SOURCE = "superusers_config"
MANUAL_SOURCE = "manual"
ALLOW_EFFECT = "allow"
_MCP_PERMISSION_UNSET = object()


async def upsert_identity_user(
    session: AsyncSession | async_scoped_session[AsyncSession],
    uid: str,
    nickname: str | None = None,
) -> IdentityUser:
    return await upsert(
        session,
        IdentityUser,
        {
            "uid": uid,
            "nickname": nickname or uid,
        },
        conflict_fields=["uid"],
        update_values={"nickname": nickname or uid},
    )


async def bind_platform_account(
    session: AsyncSession | async_scoped_session[AsyncSession],
    *,
    uid: str,
    platform_id: str,
    account_id: str,
    account_type: str = "user",
    display_name: str | None = None,
) -> PlatformAccount:
    return await upsert(
        session,
        PlatformAccount,
        {
            "uid": uid,
            "platform_id": platform_id,
            "account_id": account_id,
            "account_type": account_type,
            "display_name": display_name,
        },
        conflict_fields=["platform_id", "account_id"],
        update_values={
            "uid": uid,
            "account_type": account_type,
            "display_name": display_name,
        },
    )


async def get_user_by_platform_account(
    session: AsyncSession | async_scoped_session[AsyncSession],
    platform_id: str,
    account_id: str,
) -> IdentityUser | None:
    account = await get_one(
        session,
        PlatformAccount,
        {"platform_id": platform_id, "account_id": account_id},
    )
    if account is None:
        return None
    return await get_one(session, IdentityUser, {"uid": account.uid})


async def get_platform_account(
    session: AsyncSession | async_scoped_session[AsyncSession],
    platform_id: str,
    account_id: str,
) -> PlatformAccount | None:
    return await get_one(
        session,
        PlatformAccount,
        {"platform_id": platform_id, "account_id": account_id},
    )


async def upsert_identity_group(
    session: AsyncSession | async_scoped_session[AsyncSession],
    *,
    group_id: str,
    platform_id: str,
    display_name: str,
    parent_group_id: str | None = None,
    mcp_permission_level: MCPPermissionLevel | None | object = _MCP_PERMISSION_UNSET,
    builtin: bool = False,
    managed_by: str | None = None,
) -> PlatformIdentityGroup:
    insert_level = (
        None if mcp_permission_level is _MCP_PERMISSION_UNSET else mcp_permission_level
    )
    update_values: dict[str, object] = {
        "platform_id": platform_id,
        "parent_group_id": parent_group_id,
        "display_name": display_name,
        "builtin": builtin,
        "managed_by": managed_by,
    }
    if mcp_permission_level is not _MCP_PERMISSION_UNSET:
        update_values["mcp_permission_level"] = mcp_permission_level
    return await upsert(
        session,
        PlatformIdentityGroup,
        {
            "group_id": group_id,
            "platform_id": platform_id,
            "parent_group_id": parent_group_id,
            "display_name": display_name,
            "mcp_permission_level": insert_level,
            "builtin": builtin,
            "managed_by": managed_by,
        },
        conflict_fields=["group_id"],
        update_values=update_values,
    )


async def seed_identity_groups(
    session: AsyncSession | async_scoped_session[AsyncSession],
    seeds: Iterable[PlatformIdentityGroupSeed],
) -> None:
    await upsert_identity_group(
        session,
        group_id=SUPERUSERS_GROUP_ID,
        platform_id=SUPERUSERS_PLATFORM_ID,
        display_name="SUPERUSERS",
        builtin=True,
    )
    for seed in seeds:
        await upsert_identity_group(
            session,
            group_id=seed.group_id,
            platform_id=seed.platform_id,
            parent_group_id=seed.parent_group_id,
            display_name=seed.display_name,
            builtin=True,
        )


async def get_identity_group(
    session: AsyncSession | async_scoped_session[AsyncSession],
    group_id: str,
) -> PlatformIdentityGroup | None:
    return await get_one(session, PlatformIdentityGroup, {"group_id": group_id})


async def update_identity_group(
    session: AsyncSession | async_scoped_session[AsyncSession],
    group_id: str,
    values: dict[str, object],
) -> tuple[int, bool]:
    return await update(
        session,
        PlatformIdentityGroup,
        {"group_id": group_id},
        values,
    )


async def delete_identity_group(
    session: AsyncSession | async_scoped_session[AsyncSession],
    group_id: str,
) -> tuple[int, bool]:
    return await delete(session, PlatformIdentityGroup, {"group_id": group_id})


async def list_identity_groups(
    session: AsyncSession | async_scoped_session[AsyncSession],
    platform_id: str | None = None,
) -> list[PlatformIdentityGroup]:
    filters = {"platform_id": platform_id} if platform_id is not None else None
    return await list_items(
        session,
        PlatformIdentityGroup,
        filters,
        order_by=["group_id"],
    )


async def upsert_membership(
    session: AsyncSession | async_scoped_session[AsyncSession],
    *,
    uid: str,
    group_id: str,
    scope_type: str = "global",
    scope_id: str | None = None,
    source: str = MANUAL_SOURCE,
) -> IdentityMembership:
    filters = {
        "uid": uid,
        "group_id": group_id,
        "scope_type": scope_type,
        "scope_id": scope_id,
    }
    existing = await get_one(session, IdentityMembership, filters)
    if existing is not None:
        await update(session, IdentityMembership, filters, {"source": source})
        updated = await get_one(session, IdentityMembership, filters)
        if updated is not None:
            return updated

    return await create(
        session,
        IdentityMembership,
        uid=uid,
        group_id=group_id,
        scope_type=scope_type,
        scope_id=scope_id,
        source=source,
    )


async def delete_membership(
    session: AsyncSession | async_scoped_session[AsyncSession],
    *,
    uid: str,
    group_id: str,
    scope_type: str = "global",
    scope_id: str | None = None,
) -> tuple[int, bool]:
    return await delete(
        session,
        IdentityMembership,
        {
            "uid": uid,
            "group_id": group_id,
            "scope_type": scope_type,
            "scope_id": scope_id,
        },
    )


async def list_memberships(
    session: AsyncSession | async_scoped_session[AsyncSession],
    *,
    uid: str | None = None,
    group_id: str | None = None,
    scope_type: str | None = None,
    scope_id: str | None = None,
) -> list[IdentityMembership]:
    filters: dict[str, object] = {}
    if uid is not None:
        filters["uid"] = uid
    if group_id is not None:
        filters["group_id"] = group_id
    if scope_type is not None:
        filters["scope_type"] = scope_type
    if scope_id is not None:
        filters["scope_id"] = scope_id
    return await list_items(
        session,
        IdentityMembership,
        filters or None,
        order_by=["group_id", "uid"],
    )


async def is_superuser(
    session: AsyncSession | async_scoped_session[AsyncSession],
    uid: str,
) -> bool:
    membership = await get_one(
        session,
        IdentityMembership,
        {
            "uid": uid,
            "group_id": SUPERUSERS_GROUP_ID,
            "scope_type": "global",
            "scope_id": None,
        },
    )
    return membership is not None


async def grant_command(
    session: AsyncSession | async_scoped_session[AsyncSession],
    *,
    group_id: str,
    command_key: str,
    effect: str = ALLOW_EFFECT,
) -> PermissionGrant:
    return await upsert(
        session,
        PermissionGrant,
        {"group_id": group_id, "command_key": command_key, "effect": effect},
        conflict_fields=["group_id", "command_key"],
        update_values={"effect": effect},
    )


async def revoke_command(
    session: AsyncSession | async_scoped_session[AsyncSession],
    *,
    group_id: str,
    command_key: str,
) -> tuple[int, bool]:
    return await delete(
        session,
        PermissionGrant,
        {"group_id": group_id, "command_key": command_key},
    )


async def list_grants(
    session: AsyncSession | async_scoped_session[AsyncSession],
    *,
    group_ids: Iterable[str] | None = None,
    command_key: str | None = None,
) -> list[PermissionGrant]:
    filters: dict[str, object] = {}
    if group_ids is not None:
        filters["group_id"] = tuple(group_ids)
    if command_key is not None:
        filters["command_key"] = command_key
    return await list_items(
        session,
        PermissionGrant,
        filters or None,
        order_by=["command_key"],
    )
