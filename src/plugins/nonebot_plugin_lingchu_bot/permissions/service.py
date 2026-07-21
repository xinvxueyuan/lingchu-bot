"""Runtime permission resolution and checks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeIs

from ..core.config import plugin_config
from ..platforms import get_platform_profile, resolve_adapter_id
from ..repositories import permissions as repo
from .platforms import resolve_runtime_identity_groups
from .types import MCPPermissionLevel, PermissionContext, PermissionDecision

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session

_MCP_PERMISSION_RANK: dict[MCPPermissionLevel, int] = {
    "read": 0,
    "write_err": 1,
    "critical": 2,
}


def _is_mcp_permission_level(value: str | None) -> TypeIs[MCPPermissionLevel]:
    return value in _MCP_PERMISSION_RANK


async def resolve_user_identity(
    session: AsyncSession | async_scoped_session[AsyncSession],
    platform_id: str,
    account_id: str,
) -> Any | None:
    return await repo.get_user_by_platform_account(session, platform_id, account_id)


async def bind_platform_account(
    session: AsyncSession | async_scoped_session[AsyncSession],
    uid: str,
    platform_id: str,
    account_id: str | int,
    *,
    nickname: str | None = None,
) -> Any:
    await repo.upsert_identity_user(session, uid, nickname)
    return await repo.bind_platform_account(
        session,
        uid=uid,
        platform_id=platform_id,
        account_id=str(account_id),
        display_name=nickname,
    )


async def resolve_permission_context(
    session: AsyncSession | async_scoped_session[AsyncSession],
    bot: Any,
    event: Any,
) -> PermissionContext:
    adapter_name = _adapter_name(bot)
    adapter_id = resolve_adapter_id(adapter_name) if adapter_name is not None else None
    profile = get_platform_profile(adapter_id or "") if adapter_id is not None else None
    platform_id = profile.platform_id if profile is not None else "unknown"
    account_id = _account_id(event)
    scope_type, scope_id = _scope(event)

    uid = None
    if account_id is not None:
        user = await resolve_user_identity(session, platform_id, account_id)
        uid = getattr(user, "uid", None) if user is not None else None

    base_context = PermissionContext(
        platform_id=platform_id,
        adapter_id=adapter_id,
        account_id=account_id,
        scope_type=scope_type,
        scope_id=scope_id,
        uid=uid,
    )
    runtime_groups = await resolve_runtime_identity_groups(bot, event, base_context)
    return PermissionContext(
        platform_id=base_context.platform_id,
        adapter_id=base_context.adapter_id,
        account_id=base_context.account_id,
        scope_type=base_context.scope_type,
        scope_id=base_context.scope_id,
        uid=base_context.uid,
        runtime_group_ids=runtime_groups,
    )


async def check_permission(
    session: AsyncSession | async_scoped_session[AsyncSession],
    command_key: str,
    bot: Any,
    event: Any,
) -> PermissionDecision:
    context = await resolve_permission_context(session, bot, event)
    return await check_permission_for_context(session, command_key, context)


async def check_permission_for_context(
    session: AsyncSession | async_scoped_session[AsyncSession],
    command_key: str,
    context: PermissionContext,
) -> PermissionDecision:
    if context.uid is None:
        return PermissionDecision(allowed=False, reason="anonymous")

    if await repo.is_superuser(session, context.uid):
        return PermissionDecision(
            allowed=True,
            reason="superuser",
            uid=context.uid,
            matched_groups=frozenset({repo.SUPERUSERS_GROUP_ID}),
        )

    effective_groups = await _effective_group_ids(session, context)
    if not effective_groups:
        return PermissionDecision(
            allowed=False,
            reason="missing_grant",
            uid=context.uid,
        )

    grants = await repo.list_grants(
        session, group_ids=effective_groups, command_key=command_key
    )
    allowed_groups = frozenset(
        grant.group_id for grant in grants if grant.effect == repo.ALLOW_EFFECT
    )
    if allowed_groups:
        return PermissionDecision(
            allowed=True,
            reason="granted",
            uid=context.uid,
            matched_groups=allowed_groups,
        )
    return PermissionDecision(allowed=False, reason="missing_grant", uid=context.uid)


async def resolve_mcp_permission(
    session: AsyncSession | async_scoped_session[AsyncSession],
    context: PermissionContext,
) -> MCPPermissionLevel | None:
    if context.uid is None:
        return None
    if await repo.is_superuser(session, context.uid):
        return "critical"

    effective_groups = await _effective_group_ids(session, context)
    groups = await repo.list_identity_groups(session)
    levels: list[MCPPermissionLevel] = []
    for group in groups:
        level = group.mcp_permission_level
        if group.group_id in effective_groups and _is_mcp_permission_level(level):
            levels.append(level)
    return max(levels, key=_MCP_PERMISSION_RANK.__getitem__, default=None)


def platform_runtime_passthrough_enabled(context: PermissionContext) -> bool:
    setting = plugin_config.permission_platform_runtime_passthrough
    if isinstance(setting, bool):
        return setting
    platform_value = setting.get(context.platform_id)
    if isinstance(platform_value, bool):
        return platform_value
    return True


async def allowed_command_keys(
    session: AsyncSession | async_scoped_session[AsyncSession],
    bot: Any,
    event: Any,
    command_keys: frozenset[str],
) -> frozenset[str]:
    context = await resolve_permission_context(session, bot, event)
    if context.uid is not None and await repo.is_superuser(session, context.uid):
        return command_keys
    allowed: set[str] = set()
    for command_key in command_keys:
        decision = await check_permission_for_context(session, command_key, context)
        if decision.allowed:
            allowed.add(command_key)
    return frozenset(allowed)


def _adapter_name(bot: Any) -> str | None:
    adapter = getattr(bot, "adapter", None)
    get_name = getattr(adapter, "get_name", None)
    if get_name is None:
        return None
    try:
        return str(get_name())
    except (RuntimeError, TypeError, ValueError):
        return None


def _account_id(event: Any) -> str | None:
    user_id = getattr(event, "user_id", None)
    if user_id is not None:
        return str(user_id)
    data = getattr(event, "data", None)
    sender = getattr(data, "sender", None)
    data_user_id = getattr(sender, "user_id", None)
    if data_user_id is not None:
        return str(data_user_id)
    return None


def _scope(event: Any) -> tuple[str, str | None]:
    group_id = getattr(event, "group_id", None)
    if group_id is not None:
        return ("group", str(group_id))
    data = getattr(event, "data", None)
    peer_id = getattr(data, "peer_id", None)
    if peer_id is not None:
        return ("group", str(peer_id))
    return ("global", None)


def _membership_matches_context(membership: Any, context: PermissionContext) -> bool:
    if membership.scope_type == "global":
        return membership.scope_id is None
    return membership.scope_type == context.scope_type and (
        membership.scope_id is None or membership.scope_id == context.scope_id
    )


async def _with_ancestor_groups(
    session: AsyncSession | async_scoped_session[AsyncSession],
    group_ids: set[str],
) -> frozenset[str]:
    if not group_ids:
        return frozenset()
    groups = {
        group.group_id: group for group in await repo.list_identity_groups(session)
    }
    expanded = set(group_ids)
    stack = list(group_ids)
    while stack:
        group_id = stack.pop()
        group = groups.get(group_id)
        parent_group_id = getattr(group, "parent_group_id", None)
        if parent_group_id and parent_group_id not in expanded:
            expanded.add(parent_group_id)
            stack.append(parent_group_id)
    return frozenset(expanded)


async def _effective_group_ids(
    session: AsyncSession | async_scoped_session[AsyncSession],
    context: PermissionContext,
) -> frozenset[str]:
    if context.uid is None:
        return frozenset()
    direct_groups: set[str] = (
        set(context.runtime_group_ids)
        if platform_runtime_passthrough_enabled(context)
        else set()
    )
    for membership in await repo.list_memberships(session, uid=context.uid):
        if _membership_matches_context(membership, context):
            direct_groups.add(membership.group_id)
    return await _with_ancestor_groups(session, direct_groups)
