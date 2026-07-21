"""SUPERUSERS-only permission administration APIs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..database.models import IdentityMembership, PlatformIdentityGroup
from ..repositories import permissions as repo
from .types import IdentityGroupCreate, PermissionContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session


class PermissionDeniedError(PermissionError):
    """Raised when an actor is not allowed to administer permissions."""


def _validate_mcp_permission_level(value: object) -> None:
    if value not in {None, "read", "write_err", "critical"}:
        raise ValueError(f"Invalid MCP permission level: {value}")


async def assert_superuser(
    session: AsyncSession | async_scoped_session[AsyncSession],
    actor: str | PermissionContext,
) -> None:
    uid = actor.uid if isinstance(actor, PermissionContext) else str(actor)
    if not uid or not await repo.is_superuser(session, uid):
        raise PermissionDeniedError("SUPERUSERS permission is required")


async def create_platform_identity_group(
    session: AsyncSession | async_scoped_session[AsyncSession],
    actor: str | PermissionContext,
    request: IdentityGroupCreate,
) -> PlatformIdentityGroup:
    await assert_superuser(session, actor)
    _validate_mcp_permission_level(request.mcp_permission_level)
    actor_uid = actor.uid if isinstance(actor, PermissionContext) else str(actor)
    return await repo.upsert_identity_group(
        session,
        group_id=request.group_id,
        platform_id=request.platform_id,
        display_name=request.display_name,
        parent_group_id=request.parent_group_id,
        mcp_permission_level=request.mcp_permission_level,
        builtin=False,
        managed_by=actor_uid,
    )


async def update_platform_identity_group(
    session: AsyncSession | async_scoped_session[AsyncSession],
    actor: str | PermissionContext,
    group_id: str,
    **fields: Any,
) -> PlatformIdentityGroup:
    await assert_superuser(session, actor)
    group = await repo.get_identity_group(session, group_id)
    if group is None:
        raise ValueError(f"Unknown identity group: {group_id}")
    if group.builtin:
        raise ValueError(f"Builtin identity group cannot be updated: {group_id}")

    allowed_fields = {"display_name", "parent_group_id", "mcp_permission_level"}
    unknown_fields = fields.keys() - allowed_fields
    if unknown_fields:
        raise ValueError(f"Unknown identity group fields: {sorted(unknown_fields)}")
    values = dict(fields)
    mcp_permission_level = values.get("mcp_permission_level")
    _validate_mcp_permission_level(mcp_permission_level)
    if values:
        await repo.update_identity_group(session, group_id, values)
    updated = await repo.get_identity_group(session, group_id)
    if updated is None:
        raise ValueError(f"Unknown identity group after update: {group_id}")
    return updated


async def delete_platform_identity_group(
    session: AsyncSession | async_scoped_session[AsyncSession],
    actor: str | PermissionContext,
    group_id: str,
) -> tuple[int, bool]:
    await assert_superuser(session, actor)
    group = await repo.get_identity_group(session, group_id)
    if group is None:
        return (0, True)
    if group.builtin:
        raise ValueError(f"Builtin identity group cannot be deleted: {group_id}")
    memberships = await repo.list_memberships(session, group_id=group_id)
    grants = await repo.list_grants(session, group_ids=(group_id,))
    if memberships or grants:
        raise ValueError(f"Identity group is still in use: {group_id}")
    return await repo.delete_identity_group(session, group_id)


async def add_identity_group_member(
    session: AsyncSession | async_scoped_session[AsyncSession],
    actor: str | PermissionContext,
    uid: str,
    group_id: str,
    *,
    scope_type: str = "global",
    scope_id: str | None = None,
) -> IdentityMembership:
    await assert_superuser(session, actor)
    group = await repo.get_identity_group(session, group_id)
    if group is None:
        raise ValueError(f"Unknown identity group: {group_id}")
    return await repo.upsert_membership(
        session,
        uid=uid,
        group_id=group_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )


async def remove_identity_group_member(
    session: AsyncSession | async_scoped_session[AsyncSession],
    actor: str | PermissionContext,
    uid: str,
    group_id: str,
    *,
    scope_type: str = "global",
    scope_id: str | None = None,
) -> tuple[int, bool]:
    await assert_superuser(session, actor)
    return await repo.delete_membership(
        session,
        uid=uid,
        group_id=group_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )


async def list_identity_group_members(
    session: AsyncSession | async_scoped_session[AsyncSession],
    actor: str | PermissionContext,
    group_id: str,
    *,
    scope_type: str | None = None,
    scope_id: str | None = None,
) -> list[IdentityMembership]:
    await assert_superuser(session, actor)
    return await repo.list_memberships(
        session,
        group_id=group_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )
