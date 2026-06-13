"""Permission tree synchronization and authorization service."""

from __future__ import annotations

from asyncio import Lock
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from nonebot import get_driver, logger

from ..repositories import permissions as repository

if TYPE_CHECKING:
    from collections.abc import Iterable

    from nonebot.adapters import Bot, Event
    from nonebot.internal.matcher.matcher import Matcher

    from ..database.models import PermissionGrant, PermissionGroup, PermissionNode


ROOT_PATH = "lingchu"
GLOBAL_RESOURCE_TYPE = "global"
GROUP_RESOURCE_TYPE = "group"
SUPERUSER_RESULT = "superuser"
ALLOW_RESULT = "allowed"
DENY_RESULT = "denied"
CAPABILITY_DENY_RESULT = "capability_denied"
_default_state_ensured = False
_default_state_lock = Lock()


@dataclass(frozen=True, slots=True)
class PermissionContext:
    platform_id: str
    adapter_id: str
    command_key: str
    user_id: str | None = None
    bot_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    implementation_name: str | None = None
    native_roles: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    allowed: bool
    result: str
    reason: str
    group: PermissionGroup | None = None
    grant: PermissionGrant | None = None
    grant_node: PermissionNode | None = None


def is_superuser(user_id: str | None) -> bool:
    if user_id is None:
        return False
    try:
        superusers = get_driver().config.superusers
    except ValueError:
        return False
    return str(user_id) in {str(item) for item in superusers}


def bind_command_key(command: type[Matcher], command_key: str) -> type[Matcher]:
    setattr(command, "_lingchu_command_key", command_key)  # noqa: B010
    return command


def command_key_for(command: type[Matcher]) -> str | None:
    value = getattr(command, "_lingchu_command_key", None)
    return str(value) if value else None


def permission_context_from_event(  # noqa: PLR0913
    *,
    bot: Bot,
    event: Event,
    adapter_id: str,
    command_key: str,
    platform_id: str = "qq",
    implementation_name: str | None = None,
) -> PermissionContext:
    return PermissionContext(
        platform_id=platform_id,
        adapter_id=adapter_id,
        command_key=command_key,
        user_id=_event_user_id(event),
        bot_id=_bot_id(bot),
        resource_type=_event_resource_type(event),
        resource_id=_event_resource_id(event),
        implementation_name=implementation_name,
        native_roles=_event_native_roles(event),
    )


async def ensure_default_permission_state() -> None:
    global _default_state_ensured  # noqa: PLW0603
    if _default_state_ensured:
        return
    async with _default_state_lock:
        if _default_state_ensured:
            return
        await _sync_default_permission_state()
        _default_state_ensured = True


async def _sync_default_permission_state() -> None:
    root = await repository.upsert_node(
        path=ROOT_PATH,
        parent_id=None,
        kind="root",
        title="Lingchu",
    )
    owner_group = await repository.upsert_group(
        key=repository.DEFAULT_OWNER_GROUP_KEY,
        name="Native Owner",
        priority=900,
        is_builtin=True,
    )
    admin_group = await repository.upsert_group(
        key=repository.DEFAULT_ADMIN_GROUP_KEY,
        name="Native Admin",
        priority=800,
        is_builtin=True,
    )

    from ..handle import menu

    command_paths: dict[tuple[str, str, str | None, str], PermissionNode] = {}
    for feature in menu.MENU_FEATURES:
        for availability in feature.availability:
            platform = await _ensure_child_node(
                root,
                f"platform:{availability.platform_id}",
                kind="platform",
                title=availability.platform_id,
                platform_id=availability.platform_id,
            )
            adapter = await _ensure_child_node(
                platform,
                f"adapter:{availability.adapter_id}",
                kind="adapter",
                title=availability.adapter_id,
                platform_id=availability.platform_id,
                adapter_id=availability.adapter_id,
            )
            implementation_value = availability.implementation_name or "default"
            implementation = await _ensure_child_node(
                adapter,
                f"implementation:{implementation_value}",
                kind="implementation",
                title=implementation_value,
                platform_id=availability.platform_id,
                adapter_id=availability.adapter_id,
                implementation_name=implementation_value,
            )
            section_parent = await _ensure_menu_section_path(
                implementation,
                feature.section_id,
                platform_id=availability.platform_id,
                adapter_id=availability.adapter_id,
                implementation_name=implementation_value,
            )
            command_node = await _ensure_child_node(
                section_parent,
                f"command:{feature.command_key}",
                kind="command",
                title=feature.id,
                platform_id=availability.platform_id,
                adapter_id=availability.adapter_id,
                implementation_name=implementation_value,
                command_key=feature.command_key,
            )
            command_paths[
                (
                    availability.platform_id,
                    availability.adapter_id,
                    availability.implementation_name,
                    feature.command_key,
                )
            ] = command_node
            await repository.upsert_capability_contract(
                platform_id=availability.platform_id,
                adapter_id=availability.adapter_id,
                implementation_name=availability.implementation_name,
                command_key=feature.command_key,
                capability=str(feature.platform_capability),
                minimum_version=availability.minimum_version,
                protocol_version=availability.protocol_version,
            )

    for group in (owner_group, admin_group):
        for platform_id in sorted({item[0] for item in command_paths}):
            platform_node = await repository.get_node_by_path(
                f"{ROOT_PATH}/platform:{platform_id}"
            )
            if platform_node is not None:
                await repository.upsert_grant(
                    group_id=group.id,
                    node_id=platform_node.id,
                    resource_type=GROUP_RESOURCE_TYPE,
                )

    for native_role, group in (("owner", owner_group), ("admin", admin_group)):
        await repository.upsert_native_role_mapping(
            platform_id="qq",
            adapter_id=None,
            resource_type=GROUP_RESOURCE_TYPE,
            native_role=native_role,
            group_id=group.id,
        )


async def check_permission(context: PermissionContext) -> PermissionDecision:
    await ensure_default_permission_state()
    if is_superuser(context.user_id):
        await audit_permission(context, result=SUPERUSER_RESULT, reason="superuser")
        return PermissionDecision(
            allowed=True,
            result=SUPERUSER_RESULT,
            reason="superuser",
        )

    target_node = await repository.get_command_node(
        platform_id=context.platform_id,
        adapter_id=context.adapter_id,
        implementation_name=context.implementation_name,
        command_key=context.command_key,
    )
    if target_node is None:
        reason = "permission node not found"
        await audit_permission(context, result=DENY_RESULT, reason=reason)
        return PermissionDecision(allowed=False, result=DENY_RESULT, reason=reason)

    if not await repository.capability_contract_allows(
        platform_id=context.platform_id,
        adapter_id=context.adapter_id,
        implementation_name=context.implementation_name,
        command_key=context.command_key,
    ):
        reason = "capability contract disabled"
        await audit_permission(
            context,
            result=CAPABILITY_DENY_RESULT,
            reason=reason,
        )
        return PermissionDecision(
            allowed=False,
            result=CAPABILITY_DENY_RESULT,
            reason=reason,
        )

    if context.user_id is None:
        reason = "user id missing"
        await audit_permission(context, result=DENY_RESULT, reason=reason)
        return PermissionDecision(allowed=False, result=DENY_RESULT, reason=reason)

    group, grant, grant_node = await repository.find_matching_grant(
        platform_id=context.platform_id,
        user_id=context.user_id,
        target_node=target_node,
        resource_type=context.resource_type,
        resource_id=context.resource_id,
        native_roles=context.native_roles,
    )
    if group is None or grant is None or grant_node is None:
        reason = "no matching grant"
        await audit_permission(context, result=DENY_RESULT, reason=reason)
        return PermissionDecision(allowed=False, result=DENY_RESULT, reason=reason)

    await audit_permission(
        context,
        result=ALLOW_RESULT,
        reason="matched grant",
        group_id=group.id,
        grant_node_id=grant_node.id,
    )
    return PermissionDecision(
        allowed=True,
        result=ALLOW_RESULT,
        reason="matched grant",
        group=group,
        grant=grant,
        grant_node=grant_node,
    )


async def audit_permission(  # noqa: PLR0913
    context: PermissionContext,
    *,
    result: str,
    reason: str | None = None,
    action: str = "check_permission",
    group_id: int | None = None,
    grant_node_id: int | None = None,
    exception_summary: str | None = None,
) -> None:
    try:
        await repository.create_audit_log(
            platform_id=context.platform_id,
            adapter_id=context.adapter_id,
            implementation_name=context.implementation_name,
            bot_id=context.bot_id,
            user_id=context.user_id,
            resource_type=context.resource_type,
            resource_id=context.resource_id,
            command_key=context.command_key,
            action=action,
            result=result,
            group_id=group_id,
            grant_node_id=grant_node_id,
            reason=reason,
            exception_summary=exception_summary,
        )
    except Exception as error:  # noqa: BLE001
        logger.exception("Failed to write permission audit log: %r", error)


async def visible_command_keys(context: PermissionContext) -> frozenset[str]:
    await ensure_default_permission_state()
    if is_superuser(context.user_id):
        from ..handle.qq.group.command_triggers import COMMAND_TRIGGERS

        return frozenset(COMMAND_TRIGGERS)

    from ..handle import menu

    allowed: set[str] = set()
    for feature in menu.MENU_FEATURES:
        feature_context = PermissionContext(
            platform_id=context.platform_id,
            adapter_id=context.adapter_id,
            implementation_name=context.implementation_name,
            command_key=feature.command_key,
            user_id=context.user_id,
            bot_id=context.bot_id,
            resource_type=context.resource_type,
            resource_id=context.resource_id,
            native_roles=context.native_roles,
        )
        decision = await check_permission(feature_context)
        if decision.allowed:
            allowed.add(feature.command_key)
    return frozenset(allowed)


async def grant_group_to_node(
    *,
    group_key: str,
    node_path: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> bool:
    await ensure_default_permission_state()
    group = await repository.get_group_by_key(group_key)
    node = await repository.get_node_by_path(node_path)
    if group is None or node is None:
        return False
    await repository.upsert_grant(
        group_id=group.id,
        node_id=node.id,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    return True


async def add_group_member(
    *,
    group_key: str,
    platform_id: str,
    user_id: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
) -> bool:
    await ensure_default_permission_state()
    group = await repository.get_group_by_key(group_key)
    if group is None:
        return False
    await repository.upsert_member(
        group_id=group.id,
        platform_id=platform_id,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    return True


async def list_tree_lines(limit: int = 80) -> list[str]:
    await ensure_default_permission_state()
    nodes = await repository.list_permission_nodes(limit=limit)
    return [
        f"{node.path} [{node.kind}]"
        + (f" -> {node.command_key}" if node.command_key else "")
        for node in nodes
    ]


async def _ensure_child_node(  # noqa: PLR0913
    parent: PermissionNode,
    segment: str,
    *,
    kind: str,
    title: str | None = None,
    platform_id: str | None = None,
    adapter_id: str | None = None,
    implementation_name: str | None = None,
    command_key: str | None = None,
) -> PermissionNode:
    return await repository.upsert_node(
        path=f"{parent.path}/{segment}",
        parent_id=parent.id,
        kind=kind,
        title=title,
        platform_id=platform_id,
        adapter_id=adapter_id,
        implementation_name=implementation_name,
        command_key=command_key,
    )


async def _ensure_menu_section_path(
    implementation: PermissionNode,
    section_id: str,
    *,
    platform_id: str,
    adapter_id: str,
    implementation_name: str,
) -> PermissionNode:
    from ..handle import menu

    page_chain = _page_chain(menu.MENU_PAGES, section_id)
    parent = implementation
    if not page_chain:
        return await _ensure_child_node(
            parent,
            f"section:{section_id}",
            kind="section",
            title=section_id,
            platform_id=platform_id,
            adapter_id=adapter_id,
            implementation_name=implementation_name,
        )
    for page in page_chain:
        parent = await _ensure_child_node(
            parent,
            f"section:{page.id}",
            kind="section",
            title=page.id,
            platform_id=platform_id,
            adapter_id=adapter_id,
            implementation_name=implementation_name,
        )
    return parent


def _page_chain(pages: Iterable[Any], target_id: str) -> tuple[Any, ...]:
    for page in pages:
        if page.id == target_id:
            return (page,)
        child_chain = _page_chain(page.children, target_id)
        if child_chain:
            return (page, *child_chain)
    return ()


def _bot_id(bot: Bot) -> str | None:
    value = getattr(bot, "self_id", None)
    return None if value is None else str(value)


def _event_user_id(event: Event) -> str | None:
    try:
        return str(event.get_user_id())
    except Exception:  # noqa: BLE001
        value = getattr(event, "user_id", None)
        return None if value is None else str(value)


def _event_resource_type(event: Event) -> str | None:
    if _event_resource_id(event) is None:
        return None
    return GROUP_RESOURCE_TYPE


def _event_resource_id(event: Event) -> str | None:
    for attr in ("group_id", "guild_id", "channel_id"):
        value = getattr(event, attr, None)
        if value is not None:
            return str(value)
    data = getattr(event, "data", None)
    peer_id = getattr(data, "peer_id", None)
    return None if peer_id is None else str(peer_id)


def _event_native_roles(event: Event) -> frozenset[str]:
    sender = getattr(event, "sender", None)
    role = getattr(sender, "role", None)
    if role is None:
        data = getattr(event, "data", None)
        role = getattr(data, "sender_role", None)
    normalized = str(role).casefold() if role is not None else ""
    if normalized in {"owner", "admin", "administrator"}:
        return frozenset({"admin" if normalized == "administrator" else normalized})
    if normalized in {"member", ""}:
        return frozenset()
    return frozenset({normalized})
