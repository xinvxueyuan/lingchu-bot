from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Self, cast
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.models import (
    NativeRoleMapping,
    PermissionGrant,
    PermissionGroupMember,
    PermissionNode,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.group import common
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.group import (
    permission as permission_module,
)
from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.group.command_triggers import (
    COMMAND_TRIGGERS,
)
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
    upsert_capability_contract = AsyncMock()
    upsert_native_role_mapping = AsyncMock()
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

    assert "lingchu/platform:qq" in nodes
    assert "lingchu/platform:qq/adapter:~onebot.v11" in nodes
    assert any(path.endswith("/command:kick_member") for path in nodes)
    assert any(grant["resource_type"] == "group" for grant in grants)
    upsert_capability_contract.assert_awaited()
    upsert_native_role_mapping.assert_awaited()


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

    await permissions.ensure_default_permission_state(force=True)

    expected_forced_sync_count = 2
    assert upsert_paths.count("lingchu") == expected_forced_sync_count


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
async def test_visible_command_keys_filters_without_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(permissions, "ensure_default_permission_state", AsyncMock())
    monkeypatch.setattr(permissions, "is_superuser", lambda _user_id: False)
    visible_command_keys_for_context = AsyncMock(
        return_value=frozenset({"kick_member"})
    )
    check_permission = AsyncMock()
    monkeypatch.setattr(
        permissions.repository,
        "visible_command_keys_for_context",
        visible_command_keys_for_context,
    )
    monkeypatch.setattr(permissions, "check_permission", check_permission)

    visible = await permissions.visible_command_keys(
        permissions.PermissionContext(
            platform_id="qq",
            adapter_id="~onebot.v11",
            command_key="menu",
            user_id="100",
        )
    )

    assert visible == {"kick_member"}
    visible_command_keys_for_context.assert_awaited_once()
    check_permission.assert_not_awaited()


@pytest.mark.asyncio
async def test_visible_command_keys_superuser_sees_all_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(permissions, "ensure_default_permission_state", AsyncMock())
    monkeypatch.setattr(permissions, "is_superuser", lambda _user_id: True)
    check_permission = AsyncMock()
    monkeypatch.setattr(permissions, "check_permission", check_permission)

    visible = await permissions.visible_command_keys(
        permissions.PermissionContext(
            platform_id="qq",
            adapter_id="~onebot.v11",
            command_key="menu",
            user_id="42",
        )
    )

    assert visible == set(COMMAND_TRIGGERS)
    check_permission.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_tree_lines_adds_truncation_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(permissions, "ensure_default_permission_state", AsyncMock())
    nodes = [
        SimpleNamespace(path=f"lingchu/{index}", kind="section", command_key=None)
        for index in range(3)
    ]
    list_permission_nodes = AsyncMock(return_value=nodes)
    monkeypatch.setattr(
        permissions.repository,
        "list_permission_nodes",
        list_permission_nodes,
    )

    lines = await permissions.list_tree_lines(limit=2)

    list_permission_nodes.assert_awaited_once_with(limit=3)
    assert lines == [
        "lingchu/0 [section]",
        "lingchu/1 [section]",
        "... 已截断，使用 权限 tree <数量> 查看更多（当前 2 条）",
    ]


def test_permission_tree_limit_parser() -> None:
    custom_limit = 200

    assert permission_module._parse_positive_limit("") is None
    assert permission_module._parse_positive_limit(str(custom_limit)) == custom_limit
    assert permission_module._parse_positive_limit("0") is None
    assert permission_module._parse_positive_limit("-1") is None
    assert permission_module._parse_positive_limit("bad") is None


@pytest.mark.asyncio
async def test_permission_native_mapping_validates_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_native_role_mapping_enabled = AsyncMock()
    finish = AsyncMock()
    monkeypatch.setattr(permission_module, "is_superuser", lambda _user_id: True)
    monkeypatch.setattr(
        permission_module.repository,
        "set_native_role_mapping_enabled",
        set_native_role_mapping_enabled,
    )
    monkeypatch.setattr(permission_module.permission_cmd, "finish", finish)

    await permission_module._handle_permission(
        cast("Any", SimpleNamespace()),
        cast("Any", SimpleNamespace(get_user_id=lambda: "42")),
        "native-on",
        "invalid",
        "",
        "",
        "",
        "",
    )

    finish.assert_awaited_once_with(message="无效的角色: 仅支持 owner 或 admin")
    set_native_role_mapping_enabled.assert_not_awaited()


@pytest.mark.asyncio
async def test_permission_native_mapping_normalizes_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_native_role_mapping_enabled = AsyncMock()
    finish = AsyncMock()
    monkeypatch.setattr(permission_module, "is_superuser", lambda _user_id: True)
    monkeypatch.setattr(
        permission_module.repository,
        "set_native_role_mapping_enabled",
        set_native_role_mapping_enabled,
    )
    monkeypatch.setattr(permission_module.permission_cmd, "finish", finish)

    await permission_module._handle_permission(
        cast("Any", SimpleNamespace()),
        cast("Any", SimpleNamespace(get_user_id=lambda: "42")),
        "native-off",
        "OWNER",
        "",
        "",
        "",
        "",
    )

    set_native_role_mapping_enabled.assert_awaited_once_with(
        platform_id="qq",
        adapter_id=None,
        resource_type="group",
        native_role="owner",
        is_enabled=False,
    )
    finish.assert_awaited_once_with(message="原生身份映射已禁用: owner")


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


@pytest.mark.asyncio
async def test_visible_command_keys_for_context_uses_bulk_queries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target_node = SimpleNamespace(
        id=10,
        command_key="kick_member",
        path="lingchu/platform:qq/adapter:~onebot.v11/command:kick_member",
    )
    missing_contract_node = SimpleNamespace(
        id=9,
        command_key="leave_group",
        path="lingchu/platform:qq/adapter:~onebot.v11/command:leave_group",
    )
    contract = SimpleNamespace(
        command_key="kick_member",
        implementation_name=repository.DEFAULT_IMPLEMENTATION,
        is_enabled=True,
    )
    group = SimpleNamespace(id=20, priority=100)
    grant_node = SimpleNamespace(id=30, path="lingchu/platform:qq")
    statements: list[object] = []
    expected_query_count = 4
    responses: list[list[object]] = [
        [target_node, missing_contract_node],
        [contract],
        [(group, SimpleNamespace())],
        [(group, SimpleNamespace(), grant_node)],
    ]

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
            response_index = len(statements) - 1
            if response_index < len(responses):
                return Result(responses[response_index])
            msg = "visible_command_keys_for_context should use fixed bulk queries"
            raise AssertionError(msg)

    def get_fake_session() -> FakeSession:
        return FakeSession()

    monkeypatch.setattr(repository, "get_session", get_fake_session)

    visible = await repository.visible_command_keys_for_context(
        platform_id="qq",
        adapter_id="~onebot.v11",
        implementation_name=None,
        user_id="100",
        resource_type="group",
        resource_id="200",
        native_roles=frozenset(),
        command_keys=["kick_member", "leave_group"],
    )

    assert visible == {"kick_member"}
    assert len(statements) == expected_query_count


def test_permission_models_have_cascade_foreign_keys() -> None:
    member_group_fk = next(
        iter(PermissionGroupMember.__table__.c.group_id.foreign_keys)
    )
    grant_group_fk = next(iter(PermissionGrant.__table__.c.group_id.foreign_keys))
    grant_node_fk = next(iter(PermissionGrant.__table__.c.node_id.foreign_keys))
    native_group_fk = next(iter(NativeRoleMapping.__table__.c.group_id.foreign_keys))

    assert member_group_fk.target_fullname == "lingchu_permission_groups.id"
    assert member_group_fk.ondelete == "CASCADE"
    assert grant_group_fk.target_fullname == "lingchu_permission_groups.id"
    assert grant_group_fk.ondelete == "CASCADE"
    assert grant_node_fk.target_fullname == "lingchu_permission_nodes.id"
    assert grant_node_fk.ondelete == "CASCADE"
    assert native_group_fk.target_fullname == "lingchu_permission_groups.id"
    assert native_group_fk.ondelete == "CASCADE"
