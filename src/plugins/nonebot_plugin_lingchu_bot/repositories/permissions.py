"""Repository helpers for Lingchu's internal permission center."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from nonebot_plugin_orm import get_session
from sqlalchemy import or_, select

from ..database.models import (
    CapabilityContract,
    NativeRoleMapping,
    PermissionAuditLog,
    PermissionGrant,
    PermissionGroup,
    PermissionGroupMember,
    PermissionNode,
)
from ..database.orm_crud import create, delete, get_one, list_items, upsert
from ..database.orm_crud import update as update_rows

DEFAULT_OWNER_GROUP_KEY = "native-owner"
DEFAULT_ADMIN_GROUP_KEY = "native-admin"
DEFAULT_VALUE = "*"
DEFAULT_IMPLEMENTATION = "default"

if TYPE_CHECKING:
    from collections.abc import Iterable


def utc_now() -> datetime:
    return datetime.now(UTC)


async def upsert_node(  # noqa: PLR0913
    *,
    path: str,
    parent_id: int | None,
    kind: str,
    title: str | None = None,
    platform_id: str | None = None,
    adapter_id: str | None = None,
    implementation_name: str | None = None,
    command_key: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    is_builtin: bool = True,
    is_enabled: bool = True,
) -> PermissionNode:
    now = utc_now()
    values = {
        "path": path,
        "parent_id": parent_id,
        "kind": kind,
        "platform_id": platform_id,
        "adapter_id": adapter_id,
        "implementation_name": implementation_name,
        "command_key": command_key,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "title": title,
        "is_builtin": is_builtin,
        "is_enabled": is_enabled,
        "created_at": now,
        "updated_at": now,
    }
    await upsert(
        PermissionNode,
        values,
        conflict_fields=["path"],
        update_values={
            "parent_id": parent_id,
            "kind": kind,
            "platform_id": platform_id,
            "adapter_id": adapter_id,
            "implementation_name": implementation_name,
            "command_key": command_key,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "title": title,
            "is_builtin": is_builtin,
            "is_enabled": is_enabled,
            "updated_at": now,
        },
    )
    node = await get_node_by_path(path)
    if node is None:
        msg = f"permission node upsert did not return a row: {path}"
        raise RuntimeError(msg)
    return node


async def get_node_by_path(path: str) -> PermissionNode | None:
    return await get_one(PermissionNode, {"path": path})


async def get_command_node(
    *,
    platform_id: str,
    adapter_id: str,
    command_key: str,
    implementation_name: str | None = None,
) -> PermissionNode | None:
    conditions = [
        PermissionNode.platform_id == platform_id,
        PermissionNode.adapter_id == adapter_id,
        PermissionNode.command_key == command_key,
        PermissionNode.is_enabled.is_(True),
        or_(
            PermissionNode.implementation_name.is_(None),
            PermissionNode.implementation_name == DEFAULT_IMPLEMENTATION,
            PermissionNode.implementation_name == implementation_name,
        ),
    ]
    items = await list_items(
        PermissionNode,
        conditions=conditions,
        order_by=["-id"],
        limit=1,
    )
    return items[0] if items else None


async def list_permission_nodes(limit: int = 200) -> list[PermissionNode]:
    return await list_items(PermissionNode, order_by=["path"], limit=limit)


async def upsert_group(  # noqa: PLR0913
    *,
    key: str,
    name: str,
    parent_id: int | None = None,
    priority: int = 0,
    is_builtin: bool = False,
    is_enabled: bool = True,
) -> PermissionGroup:
    now = utc_now()
    await upsert(
        PermissionGroup,
        {
            "key": key,
            "name": name,
            "parent_id": parent_id,
            "priority": priority,
            "is_builtin": is_builtin,
            "is_enabled": is_enabled,
            "created_at": now,
            "updated_at": now,
        },
        conflict_fields=["key"],
        update_values={
            "name": name,
            "parent_id": parent_id,
            "priority": priority,
            "is_builtin": is_builtin,
            "is_enabled": is_enabled,
            "updated_at": now,
        },
    )
    group = await get_group_by_key(key)
    if group is None:
        msg = f"permission group upsert did not return a row: {key}"
        raise RuntimeError(msg)
    return group


async def get_group_by_key(key: str) -> PermissionGroup | None:
    return await get_one(PermissionGroup, {"key": key})


async def upsert_member(  # noqa: PLR0913
    *,
    group_id: int,
    platform_id: str,
    user_id: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    expires_at: datetime | None = None,
) -> PermissionGroupMember:
    now = utc_now()
    stored_resource_type = _stored_scope(resource_type)
    stored_resource_id = _stored_scope(resource_id)
    values = {
        "group_id": group_id,
        "platform_id": platform_id,
        "user_id": user_id,
        "resource_type": stored_resource_type,
        "resource_id": stored_resource_id,
        "expires_at": expires_at,
        "created_at": now,
        "updated_at": now,
    }
    await upsert(
        PermissionGroupMember,
        values,
        conflict_fields=[
            "group_id",
            "platform_id",
            "user_id",
            "resource_type",
            "resource_id",
        ],
        update_values={"expires_at": expires_at, "updated_at": now},
    )
    member = await get_one(
        PermissionGroupMember,
        {
            "group_id": group_id,
            "platform_id": platform_id,
            "user_id": user_id,
            "resource_type": stored_resource_type,
            "resource_id": stored_resource_id,
        },
    )
    if member is None:
        msg = "permission group member upsert did not return a row"
        raise RuntimeError(msg)
    return member


async def remove_member(
    *,
    group_id: int,
    platform_id: str,
    user_id: str,
    resource_type: str | None,
    resource_id: str | None,
) -> tuple[int, bool]:
    stored_resource_type = _stored_scope(resource_type)
    stored_resource_id = _stored_scope(resource_id)
    return await delete(
        PermissionGroupMember,
        {
            "group_id": group_id,
            "platform_id": platform_id,
            "user_id": user_id,
            "resource_type": stored_resource_type,
            "resource_id": stored_resource_id,
        },
    )


async def upsert_grant(  # noqa: PLR0913
    *,
    group_id: int,
    node_id: int,
    resource_type: str | None = None,
    resource_id: str | None = None,
    is_enabled: bool = True,
    expires_at: datetime | None = None,
) -> PermissionGrant:
    now = utc_now()
    stored_resource_type = _stored_scope(resource_type)
    stored_resource_id = _stored_scope(resource_id)
    values = {
        "group_id": group_id,
        "node_id": node_id,
        "resource_type": stored_resource_type,
        "resource_id": stored_resource_id,
        "is_enabled": is_enabled,
        "expires_at": expires_at,
        "created_at": now,
        "updated_at": now,
    }
    await upsert(
        PermissionGrant,
        values,
        conflict_fields=["group_id", "node_id", "resource_type", "resource_id"],
        update_values={
            "is_enabled": is_enabled,
            "expires_at": expires_at,
            "updated_at": now,
        },
    )
    grant = await get_one(
        PermissionGrant,
        {
            "group_id": group_id,
            "node_id": node_id,
            "resource_type": stored_resource_type,
            "resource_id": stored_resource_id,
        },
    )
    if grant is None:
        msg = "permission grant upsert did not return a row"
        raise RuntimeError(msg)
    return grant


async def upsert_capability_contract(  # noqa: PLR0913
    *,
    platform_id: str,
    adapter_id: str,
    command_key: str,
    capability: str,
    implementation_name: str | None = None,
    minimum_version: str | None = None,
    protocol_version: str | None = None,
    is_enabled: bool = True,
) -> CapabilityContract:
    now = utc_now()
    stored_implementation_name = implementation_name or DEFAULT_IMPLEMENTATION
    values = {
        "platform_id": platform_id,
        "adapter_id": adapter_id,
        "implementation_name": stored_implementation_name,
        "command_key": command_key,
        "capability": capability,
        "minimum_version": minimum_version,
        "protocol_version": protocol_version,
        "is_enabled": is_enabled,
        "created_at": now,
        "updated_at": now,
    }
    await upsert(
        CapabilityContract,
        values,
        conflict_fields=[
            "platform_id",
            "adapter_id",
            "implementation_name",
            "command_key",
        ],
        update_values={
            "capability": capability,
            "minimum_version": minimum_version,
            "protocol_version": protocol_version,
            "is_enabled": is_enabled,
            "updated_at": now,
        },
    )
    contract = await get_one(
        CapabilityContract,
        {
            "platform_id": platform_id,
            "adapter_id": adapter_id,
            "implementation_name": stored_implementation_name,
            "command_key": command_key,
        },
    )
    if contract is None:
        msg = "capability contract upsert did not return a row"
        raise RuntimeError(msg)
    return contract


async def upsert_native_role_mapping(  # noqa: PLR0913
    *,
    platform_id: str,
    adapter_id: str | None,
    resource_type: str,
    native_role: str,
    group_id: int | None,
    is_enabled: bool = True,
) -> NativeRoleMapping:
    now = utc_now()
    stored_adapter_id = adapter_id or DEFAULT_VALUE
    values = {
        "platform_id": platform_id,
        "adapter_id": stored_adapter_id,
        "resource_type": resource_type,
        "native_role": native_role,
        "group_id": group_id,
        "is_enabled": is_enabled,
        "created_at": now,
        "updated_at": now,
    }
    await upsert(
        NativeRoleMapping,
        values,
        conflict_fields=["platform_id", "adapter_id", "resource_type", "native_role"],
        update_values={
            "group_id": group_id,
            "is_enabled": is_enabled,
            "updated_at": now,
        },
    )
    mapping = await get_one(
        NativeRoleMapping,
        {
            "platform_id": platform_id,
            "adapter_id": stored_adapter_id,
            "resource_type": resource_type,
            "native_role": native_role,
        },
    )
    if mapping is None:
        msg = "native role mapping upsert did not return a row"
        raise RuntimeError(msg)
    return mapping


async def set_native_role_mapping_enabled(
    *,
    platform_id: str,
    adapter_id: str | None,
    resource_type: str,
    native_role: str,
    is_enabled: bool,
) -> tuple[int, bool]:
    stored_adapter_id = adapter_id or DEFAULT_VALUE
    return await update_rows(
        NativeRoleMapping,
        {
            "platform_id": platform_id,
            "adapter_id": stored_adapter_id,
            "resource_type": resource_type,
            "native_role": native_role,
        },
        {"is_enabled": is_enabled, "updated_at": utc_now()},
    )


async def create_audit_log(**fields: Any) -> PermissionAuditLog:
    return await create(
        PermissionAuditLog,
        created_at=utc_now(),
        **fields,
    )


async def find_matching_grant(  # noqa: PLR0913
    *,
    platform_id: str,
    user_id: str,
    target_node: PermissionNode,
    resource_type: str | None,
    resource_id: str | None,
    native_roles: frozenset[str] = frozenset(),
) -> tuple[PermissionGroup | None, PermissionGrant | None, PermissionNode | None]:
    now = utc_now()
    async with get_session() as session:
        member_stmt = (
            select(PermissionGroup, PermissionGroupMember)
            .join(
                PermissionGroupMember,
                PermissionGroup.id == PermissionGroupMember.group_id,
            )
            .where(
                PermissionGroup.is_enabled.is_(True),
                PermissionGroupMember.platform_id == platform_id,
                PermissionGroupMember.user_id == user_id,
                or_(
                    PermissionGroupMember.resource_type == DEFAULT_VALUE,
                    PermissionGroupMember.resource_type == resource_type,
                ),
                or_(
                    PermissionGroupMember.resource_id == DEFAULT_VALUE,
                    PermissionGroupMember.resource_id == resource_id,
                ),
                or_(
                    PermissionGroupMember.expires_at.is_(None),
                    PermissionGroupMember.expires_at > now,
                ),
            )
            .order_by(PermissionGroup.priority.desc())
        )
        groups: list[PermissionGroup] = [
            row[0] for row in (await session.execute(member_stmt)).all()
        ]

        if native_roles:
            # Native role mappings intentionally define how a platform role label maps
            # to an internal group for the whole resource type. Concrete scope still
            # comes from the event's native role on the current resource plus grant
            # resource_type/resource_id matching below.
            native_stmt = (
                select(PermissionGroup)
                .join(
                    NativeRoleMapping,
                    PermissionGroup.id == NativeRoleMapping.group_id,
                )
                .where(
                    PermissionGroup.is_enabled.is_(True),
                    NativeRoleMapping.platform_id == platform_id,
                    or_(
                        NativeRoleMapping.adapter_id == DEFAULT_VALUE,
                        NativeRoleMapping.adapter_id == target_node.adapter_id,
                    ),
                    NativeRoleMapping.resource_type == (resource_type or "global"),
                    NativeRoleMapping.native_role.in_(native_roles),
                    NativeRoleMapping.is_enabled.is_(True),
                )
                .order_by(PermissionGroup.priority.desc())
            )
            groups.extend((await session.execute(native_stmt)).scalars())

        group_ids = list(dict.fromkeys(group.id for group in groups))
        if not group_ids:
            return None, None, None

        grant_stmt = (
            select(PermissionGroup, PermissionGrant, PermissionNode)
            .join(PermissionGrant, PermissionGroup.id == PermissionGrant.group_id)
            .join(PermissionNode, PermissionGrant.node_id == PermissionNode.id)
            .where(
                PermissionGroup.id.in_(group_ids),
                PermissionGrant.is_enabled.is_(True),
                PermissionNode.is_enabled.is_(True),
                or_(
                    PermissionGrant.resource_type == DEFAULT_VALUE,
                    PermissionGrant.resource_type == resource_type,
                ),
                or_(
                    PermissionGrant.resource_id == DEFAULT_VALUE,
                    PermissionGrant.resource_id == resource_id,
                ),
                or_(
                    PermissionGrant.expires_at.is_(None),
                    PermissionGrant.expires_at > now,
                ),
            )
            .order_by(PermissionGroup.priority.desc(), PermissionNode.path)
        )
        grants = (await session.execute(grant_stmt)).all()
        for group, grant, node in grants:
            if target_node.path == node.path or target_node.path.startswith(
                f"{node.path}/"
            ):
                return group, grant, node
    return None, None, None


async def visible_command_keys_for_context(  # noqa: PLR0913
    *,
    platform_id: str,
    adapter_id: str,
    implementation_name: str | None,
    user_id: str | None,
    resource_type: str | None,
    resource_id: str | None,
    native_roles: frozenset[str],
    command_keys: Iterable[str],
) -> frozenset[str]:
    keys = list(dict.fromkeys(command_keys))
    if not keys or user_id is None:
        return frozenset()

    now = utc_now()
    async with get_session() as session:
        node_stmt = (
            select(PermissionNode)
            .where(
                PermissionNode.platform_id == platform_id,
                PermissionNode.adapter_id == adapter_id,
                PermissionNode.command_key.in_(keys),
                PermissionNode.is_enabled.is_(True),
                or_(
                    PermissionNode.implementation_name.is_(None),
                    PermissionNode.implementation_name == DEFAULT_IMPLEMENTATION,
                    PermissionNode.implementation_name == implementation_name,
                ),
            )
            .order_by(PermissionNode.id.desc())
        )
        command_nodes = _select_command_nodes(
            (await session.execute(node_stmt)).scalars(),
            implementation_name,
        )
        if not command_nodes:
            return frozenset()

        contract_stmt = select(CapabilityContract).where(
            CapabilityContract.platform_id == platform_id,
            CapabilityContract.adapter_id == adapter_id,
            CapabilityContract.command_key.in_(command_nodes),
        )
        enabled_contract_keys = {
            contract.command_key
            for contract in (await session.execute(contract_stmt)).scalars()
            if contract.is_enabled
            and contract.implementation_name
            in {DEFAULT_IMPLEMENTATION, implementation_name}
        }
        if not enabled_contract_keys:
            return frozenset()

        group_ids = await _matching_group_ids(
            session=session,
            platform_id=platform_id,
            adapter_id=adapter_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            native_roles=native_roles,
            now=now,
        )
        if not group_ids:
            return frozenset()

        grant_stmt = (
            select(PermissionGroup, PermissionGrant, PermissionNode)
            .join(PermissionGrant, PermissionGroup.id == PermissionGrant.group_id)
            .join(PermissionNode, PermissionGrant.node_id == PermissionNode.id)
            .where(
                PermissionGroup.id.in_(group_ids),
                PermissionGrant.is_enabled.is_(True),
                PermissionNode.is_enabled.is_(True),
                or_(
                    PermissionGrant.resource_type == DEFAULT_VALUE,
                    PermissionGrant.resource_type == resource_type,
                ),
                or_(
                    PermissionGrant.resource_id == DEFAULT_VALUE,
                    PermissionGrant.resource_id == resource_id,
                ),
                or_(
                    PermissionGrant.expires_at.is_(None),
                    PermissionGrant.expires_at > now,
                ),
            )
            .order_by(PermissionGroup.priority.desc(), PermissionNode.path)
        )
        grant_nodes = [row[2] for row in (await session.execute(grant_stmt)).all()]

    allowed: set[str] = set()
    for command_key, target_node in command_nodes.items():
        if command_key not in enabled_contract_keys:
            continue
        if any(_node_covers(grant_node, target_node) for grant_node in grant_nodes):
            allowed.add(command_key)
    return frozenset(allowed)


async def capability_contract_allows(
    *,
    platform_id: str,
    adapter_id: str,
    command_key: str,
    implementation_name: str | None,
) -> bool:
    contracts = await list_items(
        CapabilityContract,
        {
            "platform_id": platform_id,
            "adapter_id": adapter_id,
            "command_key": command_key,
        },
        limit=100,
    )
    if not contracts:
        return False
    return any(
        contract.is_enabled
        and contract.implementation_name
        in {DEFAULT_IMPLEMENTATION, implementation_name}
        for contract in contracts
    )


async def _matching_group_ids(  # noqa: PLR0913
    *,
    session: Any,
    platform_id: str,
    adapter_id: str,
    user_id: str,
    resource_type: str | None,
    resource_id: str | None,
    native_roles: frozenset[str],
    now: datetime,
) -> list[int]:
    member_stmt = (
        select(PermissionGroup, PermissionGroupMember)
        .join(
            PermissionGroupMember,
            PermissionGroup.id == PermissionGroupMember.group_id,
        )
        .where(
            PermissionGroup.is_enabled.is_(True),
            PermissionGroupMember.platform_id == platform_id,
            PermissionGroupMember.user_id == user_id,
            or_(
                PermissionGroupMember.resource_type == DEFAULT_VALUE,
                PermissionGroupMember.resource_type == resource_type,
            ),
            or_(
                PermissionGroupMember.resource_id == DEFAULT_VALUE,
                PermissionGroupMember.resource_id == resource_id,
            ),
            or_(
                PermissionGroupMember.expires_at.is_(None),
                PermissionGroupMember.expires_at > now,
            ),
        )
        .order_by(PermissionGroup.priority.desc())
    )
    groups: list[PermissionGroup] = [
        row[0] for row in (await session.execute(member_stmt)).all()
    ]

    if native_roles:
        native_stmt = (
            select(PermissionGroup)
            .join(
                NativeRoleMapping,
                PermissionGroup.id == NativeRoleMapping.group_id,
            )
            .where(
                PermissionGroup.is_enabled.is_(True),
                NativeRoleMapping.platform_id == platform_id,
                or_(
                    NativeRoleMapping.adapter_id == DEFAULT_VALUE,
                    NativeRoleMapping.adapter_id == adapter_id,
                ),
                NativeRoleMapping.resource_type == (resource_type or "global"),
                NativeRoleMapping.native_role.in_(native_roles),
                NativeRoleMapping.is_enabled.is_(True),
            )
            .order_by(PermissionGroup.priority.desc())
        )
        groups.extend((await session.execute(native_stmt)).scalars())

    return list(dict.fromkeys(group.id for group in groups))


def _node_covers(grant_node: PermissionNode, target_node: PermissionNode) -> bool:
    return target_node.path == grant_node.path or target_node.path.startswith(
        f"{grant_node.path}/"
    )


def _select_command_nodes(
    nodes: Iterable[PermissionNode],
    implementation_name: str | None,
) -> dict[str, PermissionNode]:
    command_nodes: dict[str, PermissionNode] = {}
    for node in nodes:
        if node.command_key is None:
            continue
        current = command_nodes.get(node.command_key)
        if current is None or _implementation_rank(
            getattr(node, "implementation_name", None),
            implementation_name,
        ) > _implementation_rank(
            getattr(current, "implementation_name", None),
            implementation_name,
        ):
            command_nodes[node.command_key] = node
    return command_nodes


def _implementation_rank(value: str | None, target: str | None) -> int:
    if target is not None and value == target:
        return 2
    if value == DEFAULT_IMPLEMENTATION:
        return 1
    if value is None:
        return 0
    return -1


def _stored_scope(value: str | None) -> str:
    return value or DEFAULT_VALUE
