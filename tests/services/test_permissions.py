from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.services import permissions


@pytest.mark.asyncio
async def test_default_permission_state_syncs_menu_tree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes: dict[str, SimpleNamespace] = {}
    grants: list[dict[str, object]] = []

    async def upsert_node(**fields: object) -> SimpleNamespace:
        node = SimpleNamespace(id=len(nodes) + 1, **fields)
        nodes[str(fields["path"])] = node
        return node

    async def get_node_by_path(path: str) -> SimpleNamespace | None:
        return nodes.get(path)

    async def upsert_group(**fields: object) -> SimpleNamespace:
        return SimpleNamespace(
            id=1 if fields["key"] == "native-owner" else 2,
            **fields,
        )

    async def upsert_grant(**fields: object) -> SimpleNamespace:
        grants.append(fields)
        return SimpleNamespace(id=len(grants), **fields)

    monkeypatch.setattr(permissions.repository, "upsert_node", upsert_node)
    monkeypatch.setattr(permissions.repository, "get_node_by_path", get_node_by_path)
    monkeypatch.setattr(permissions.repository, "upsert_group", upsert_group)
    monkeypatch.setattr(permissions.repository, "upsert_grant", upsert_grant)
    monkeypatch.setattr(
        permissions.repository,
        "upsert_capability_contract",
        AsyncMock(),
    )
    monkeypatch.setattr(
        permissions.repository,
        "upsert_native_role_mapping",
        AsyncMock(),
    )

    await permissions.ensure_default_permission_state()

    assert "lingchu/platform:qq" in nodes
    assert "lingchu/platform:qq/adapter:~onebot.v11" in nodes
    assert any(path.endswith("/command:kick_member") for path in nodes)
    assert any(grant["resource_type"] == "group" for grant in grants)


@pytest.mark.asyncio
async def test_check_permission_allows_superuser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(permissions, "ensure_default_permission_state", AsyncMock())
    monkeypatch.setattr(
        permissions,
        "get_driver",
        lambda: SimpleNamespace(config=SimpleNamespace(superusers={"42"})),
    )
    audit = AsyncMock()
    monkeypatch.setattr(permissions, "audit_permission", audit)

    decision = await permissions.check_permission(
        permissions.PermissionContext(
            platform_id="qq",
            adapter_id="~onebot.v11",
            command_key="kick_member",
            user_id="42",
        )
    )

    assert decision.allowed is True
    assert decision.result == permissions.SUPERUSER_RESULT
    audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_permission_allows_matching_grant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = SimpleNamespace(
        id=10,
        path="lingchu/platform:qq/adapter:~onebot.v11/command:kick_member",
        adapter_id="~onebot.v11",
    )
    group = SimpleNamespace(id=20)
    grant = SimpleNamespace(id=30)
    grant_node = SimpleNamespace(id=40, path="lingchu/platform:qq")

    monkeypatch.setattr(permissions, "ensure_default_permission_state", AsyncMock())
    monkeypatch.setattr(
        permissions,
        "get_driver",
        lambda: SimpleNamespace(config=SimpleNamespace(superusers=set())),
    )
    monkeypatch.setattr(permissions, "audit_permission", AsyncMock())
    monkeypatch.setattr(
        permissions.repository,
        "get_command_node",
        AsyncMock(return_value=target),
    )
    monkeypatch.setattr(
        permissions.repository,
        "capability_contract_allows",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        permissions.repository,
        "find_matching_grant",
        AsyncMock(return_value=(group, grant, grant_node)),
    )

    decision = await permissions.check_permission(
        permissions.PermissionContext(
            platform_id="qq",
            adapter_id="~onebot.v11",
            command_key="kick_member",
            user_id="100",
            resource_type="group",
            resource_id="200",
        )
    )

    assert decision.allowed is True
    assert decision.group is group
    assert decision.grant_node is grant_node


@pytest.mark.asyncio
async def test_check_permission_denies_disabled_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(permissions, "ensure_default_permission_state", AsyncMock())
    monkeypatch.setattr(
        permissions,
        "get_driver",
        lambda: SimpleNamespace(config=SimpleNamespace(superusers=set())),
    )
    monkeypatch.setattr(permissions, "audit_permission", AsyncMock())
    monkeypatch.setattr(
        permissions.repository,
        "get_command_node",
        AsyncMock(
            return_value=SimpleNamespace(
                id=1,
                path="lingchu/platform:qq",
                adapter_id="~onebot.v11",
            )
        ),
    )
    monkeypatch.setattr(
        permissions.repository,
        "capability_contract_allows",
        AsyncMock(return_value=False),
    )

    decision = await permissions.check_permission(
        permissions.PermissionContext(
            platform_id="qq",
            adapter_id="~onebot.v11",
            command_key="kick_member",
            user_id="100",
        )
    )

    assert decision.allowed is False
    assert decision.result == permissions.CAPABILITY_DENY_RESULT
