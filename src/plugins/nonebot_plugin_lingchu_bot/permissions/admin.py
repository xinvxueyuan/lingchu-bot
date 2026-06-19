"""SUPERUSERS-only permission administration APIs."""

# ruff: noqa: TRY003, TC001

from __future__ import annotations

from typing import Any

from ..database.models import IdentityMembership, PlatformIdentityGroup
from ..repositories import permissions as repo
from .types import PermissionContext


class PermissionDeniedError(PermissionError):
    """Raised when an actor is not allowed to administer permissions."""


async def assert_superuser(actor: str | PermissionContext) -> None:
    uid = actor.uid if isinstance(actor, PermissionContext) else str(actor)
    if not uid or not await repo.is_superuser(uid):
        raise PermissionDeniedError("SUPERUSERS permission is required")


async def create_platform_identity_group(
    actor: str | PermissionContext,
    platform_id: str,
    group_id: str,
    display_name: str,
    parent_group_id: str | None = None,
) -> PlatformIdentityGroup:
    await assert_superuser(actor)
    actor_uid = actor.uid if isinstance(actor, PermissionContext) else str(actor)
    return await repo.upsert_identity_group(
        group_id=group_id,
        platform_id=platform_id,
        display_name=display_name,
        parent_group_id=parent_group_id,
        builtin=False,
        managed_by=actor_uid,
    )


async def update_platform_identity_group(
    actor: str | PermissionContext,
    group_id: str,
    **fields: Any,
) -> PlatformIdentityGroup:
    await assert_superuser(actor)
    group = await repo.get_identity_group(group_id)
    if group is None:
        raise ValueError(f"Unknown identity group: {group_id}")
    if group.builtin:
        raise ValueError(f"Builtin identity group cannot be updated: {group_id}")

    allowed_fields = {"display_name", "parent_group_id"}
    values = {key: value for key, value in fields.items() if key in allowed_fields}
    if values:
        await repo.update_identity_group(group_id, values)
    updated = await repo.get_identity_group(group_id)
    if updated is None:
        raise ValueError(f"Unknown identity group after update: {group_id}")
    return updated


async def delete_platform_identity_group(
    actor: str | PermissionContext,
    group_id: str,
) -> tuple[int, bool]:
    await assert_superuser(actor)
    group = await repo.get_identity_group(group_id)
    if group is None:
        return (0, True)
    if group.builtin:
        raise ValueError(f"Builtin identity group cannot be deleted: {group_id}")
    memberships = await repo.list_memberships(group_id=group_id)
    grants = await repo.list_grants(group_ids=(group_id,))
    if memberships or grants:
        raise ValueError(f"Identity group is still in use: {group_id}")
    return await repo.delete_identity_group(group_id)


async def add_identity_group_member(
    actor: str | PermissionContext,
    uid: str,
    group_id: str,
    *,
    scope_type: str = "global",
    scope_id: str | None = None,
) -> IdentityMembership:
    await assert_superuser(actor)
    group = await repo.get_identity_group(group_id)
    if group is None:
        raise ValueError(f"Unknown identity group: {group_id}")
    return await repo.upsert_membership(
        uid=uid,
        group_id=group_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )


async def remove_identity_group_member(
    actor: str | PermissionContext,
    uid: str,
    group_id: str,
    *,
    scope_type: str = "global",
    scope_id: str | None = None,
) -> tuple[int, bool]:
    await assert_superuser(actor)
    return await repo.delete_membership(
        uid=uid,
        group_id=group_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )


async def list_identity_group_members(
    actor: str | PermissionContext,
    group_id: str,
    *,
    scope_type: str | None = None,
    scope_id: str | None = None,
) -> list[IdentityMembership]:
    await assert_superuser(actor)
    return await repo.list_memberships(
        group_id=group_id,
        scope_type=scope_type,
        scope_id=scope_id,
    )
