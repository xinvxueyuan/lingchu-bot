from __future__ import annotations

from types import SimpleNamespace
from typing import Self, cast
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.models import (
    PermissionGrant,
    PermissionGroupMember,
    PermissionNode,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.group import common
from src.plugins.nonebot_plugin_lingchu_bot.repositories import (
    permissions as repository,
)
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
    monkeypatch.setattr(permissions, "_default_state_ensured", False)

    await permissions.ensure_default_permission_state()

    assert "lingchu/platform:qq" in nodes
    assert "lingchu/platform:qq/adapter:~onebot.v11" in nodes
    assert any(path.endswith("/command:kick_member") for path in nodes)
    assert any(grant["resource_type"] == "group" for grant in grants)


@pytest.mark.asyncio
async def test_default_permission_state_is_cached_after_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes: dict[str, SimpleNamespace] = {}
    upsert_paths: list[str] = []

    async def upsert_node(**fields: object) -> SimpleNamespace:
        upsert_paths.append(str(fields["path"]))
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

    upsert_grant = AsyncMock()
    upsert_capability_contract = AsyncMock()
    upsert_native_role_mapping = AsyncMock()
    monkeypatch.setattr(permissions.repository, "upsert_node", upsert_node)
    monkeypatch.setattr(permissions.repository, "get_node_by_path", get_node_by_path)
    monkeypatch.setattr(permissions.repository, "upsert_group", upsert_group)
    monkeypatch.setattr(permissions.repository, "upsert_grant", upsert_grant)
    monkeypatch.setattr(
        permissions.repository,
        "upsert_capability_contract",
        upsert_capability_contract,
    )
    monkeypatch.setattr(
        permissions.repository,
        "upsert_native_role_mapping",
        upsert_native_role_mapping,
    )
    monkeypatch.setattr(permissions, "_default_state_ensured", False)

    await permissions.ensure_default_permission_state()
    await permissions.ensure_default_permission_state()

    assert upsert_grant.await_count > 0
    upsert_capability_contract.assert_awaited()
    upsert_native_role_mapping.assert_awaited()
    assert upsert_paths.count("lingchu") == 1


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


@pytest.mark.asyncio
async def test_permission_guard_fails_closed_when_context_missing() -> None:
    async def handler() -> None:
        msg = "handler should not run without permission context"
        raise AssertionError(msg)

    command = SimpleNamespace(
        _lingchu_command_key="kick_member",
        finish=AsyncMock(return_value=None),
    )

    wrapped = common._permission_guard(
        cast("common.GroupCommand", command),
        "~onebot.v11",
        handler,
    )

    await wrapped()

    command.finish.assert_awaited_once_with(message="系统错误：无法验证权限")


@pytest.mark.asyncio
async def test_find_matching_grant_uses_global_group_priority(  # noqa: C901
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    low_group = SimpleNamespace(id=1, priority=100)
    high_group = SimpleNamespace(id=2, priority=900)
    high_grant = SimpleNamespace(id=20)
    high_node = SimpleNamespace(id=30, path="lingchu/platform:qq")
    target_node = SimpleNamespace(
        id=40,
        adapter_id="~onebot.v11",
        path="lingchu/platform:qq/adapter:~onebot.v11/command:kick_member",
    )
    member_query_count = 1
    native_query_count = 2
    grant_query_count = 3
    statements: list[object] = []

    class Result:
        def __init__(self, rows: list[object]) -> None:
            self._rows = rows

        def all(self) -> list[object]:
            return self._rows

        def scalars(self) -> list[object]:
            return self._rows

    class FakeSession:
        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_exc: object) -> None:
            return None

        async def execute(self, statement: object) -> Result:
            statements.append(statement)
            if len(statements) == member_query_count:
                return Result([(low_group, SimpleNamespace())])
            if len(statements) == native_query_count:
                return Result([high_group])
            if len(statements) == grant_query_count:
                return Result([(high_group, high_grant, high_node)])
            msg = "find_matching_grant should issue one grant query"
            raise AssertionError(msg)

    def get_fake_session() -> FakeSession:
        return FakeSession()

    monkeypatch.setattr(repository, "get_session", get_fake_session)

    group, grant, node = await repository.find_matching_grant(
        platform_id="qq",
        user_id="100",
        target_node=cast("PermissionNode", target_node),
        resource_type="group",
        resource_id="200",
        native_roles=frozenset({"owner"}),
    )

    assert group is high_group
    assert grant is high_grant
    assert node is high_node
    assert len(statements) == grant_query_count


def test_permission_models_have_cascade_foreign_keys() -> None:
    member_group_fk = next(
        iter(PermissionGroupMember.__table__.c.group_id.foreign_keys)
    )
    grant_group_fk = next(iter(PermissionGrant.__table__.c.group_id.foreign_keys))
    grant_node_fk = next(iter(PermissionGrant.__table__.c.node_id.foreign_keys))

    assert member_group_fk.target_fullname == "lingchu_permission_groups.id"
    assert member_group_fk.ondelete == "CASCADE"
    assert grant_group_fk.target_fullname == "lingchu_permission_groups.id"
    assert grant_group_fk.ondelete == "CASCADE"
    assert grant_node_fk.target_fullname == "lingchu_permission_nodes.id"
    assert grant_node_fk.ondelete == "CASCADE"
