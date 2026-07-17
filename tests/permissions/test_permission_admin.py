from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.permissions.admin import (
    PermissionDeniedError,
    add_identity_group_member,
    assert_superuser,
    create_platform_identity_group,
    delete_platform_identity_group,
    list_identity_group_members,
    remove_identity_group_member,
    update_platform_identity_group,
)
from src.plugins.nonebot_plugin_lingchu_bot.permissions.types import (
    IdentityGroupCreate,
    MCPPermissionLevel,
    PermissionContext,
)
from src.plugins.nonebot_plugin_lingchu_bot.repositories import permissions as repo


@pytest.mark.asyncio
async def test_non_superuser_cannot_create_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=False))

    with pytest.raises(PermissionDeniedError):
        await create_platform_identity_group(
            "userA", IdentityGroupCreate("qq", "qq.custom", "自定义")
        )


@pytest.mark.asyncio
async def test_superuser_can_create_group(monkeypatch: pytest.MonkeyPatch) -> None:
    created = SimpleNamespace(group_id="qq.custom")
    upsert = AsyncMock(return_value=created)
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    monkeypatch.setattr(repo, "upsert_identity_group", upsert)

    result = await create_platform_identity_group(
        "userA",
        IdentityGroupCreate(
            "qq", "qq.custom", "自定义", mcp_permission_level="critical"
        ),
    )

    assert result is created
    assert upsert.await_args is not None
    assert upsert.await_args.kwargs["builtin"] is False
    assert upsert.await_args.kwargs["managed_by"] == "userA"
    assert upsert.await_args.kwargs["mcp_permission_level"] == "critical"


@pytest.mark.asyncio
async def test_create_group_rejects_invalid_mcp_permission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    request = IdentityGroupCreate(
        "qq",
        "qq.custom",
        "自定义",
        mcp_permission_level=cast("MCPPermissionLevel", "root"),
    )

    with pytest.raises(ValueError, match="Invalid MCP permission level"):
        await create_platform_identity_group("userA", request)


@pytest.mark.asyncio
async def test_builtin_group_cannot_be_updated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    monkeypatch.setattr(
        repo,
        "get_identity_group",
        AsyncMock(return_value=SimpleNamespace(group_id="qq.group", builtin=True)),
    )

    with pytest.raises(ValueError, match="Builtin"):
        await update_platform_identity_group("userA", "qq.group", display_name="x")


@pytest.mark.asyncio
async def test_group_in_use_cannot_be_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    monkeypatch.setattr(
        repo,
        "get_identity_group",
        AsyncMock(return_value=SimpleNamespace(group_id="qq.custom", builtin=False)),
    )
    monkeypatch.setattr(repo, "list_memberships", AsyncMock(return_value=[object()]))
    monkeypatch.setattr(repo, "list_grants", AsyncMock(return_value=[]))

    with pytest.raises(ValueError, match="still in use"):
        await delete_platform_identity_group("userA", "qq.custom")


@pytest.mark.asyncio
async def test_superuser_can_add_member(monkeypatch: pytest.MonkeyPatch) -> None:
    membership = SimpleNamespace(uid="userB", group_id="qq.custom")
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    monkeypatch.setattr(
        repo,
        "get_identity_group",
        AsyncMock(return_value=SimpleNamespace(group_id="qq.custom")),
    )
    monkeypatch.setattr(repo, "upsert_membership", AsyncMock(return_value=membership))

    result = await add_identity_group_member("userA", "userB", "qq.custom")

    assert result is membership


@pytest.mark.asyncio
async def test_update_unknown_group_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    monkeypatch.setattr(repo, "get_identity_group", AsyncMock(return_value=None))

    with pytest.raises(ValueError, match="Unknown identity group"):
        await update_platform_identity_group("userA", "qq.unknown", display_name="x")


@pytest.mark.asyncio
async def test_update_group_rejects_unknown_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = SimpleNamespace(group_id="qq.custom", builtin=False)
    updated = SimpleNamespace(group_id="qq.custom", builtin=False, display_name="new")
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    monkeypatch.setattr(
        repo,
        "get_identity_group",
        AsyncMock(side_effect=[original, updated]),
    )
    update_mock = AsyncMock(return_value=(1, True))
    monkeypatch.setattr(repo, "update_identity_group", update_mock)

    with pytest.raises(ValueError, match="Unknown identity group fields"):
        await update_platform_identity_group(
            "userA",
            "qq.custom",
            display_name="new",
            invalid_field="ignored",
        )

    update_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_group_skips_when_no_allowed_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = SimpleNamespace(group_id="qq.custom", builtin=False)
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    monkeypatch.setattr(
        repo,
        "get_identity_group",
        AsyncMock(side_effect=[group, group]),
    )
    update_mock = AsyncMock(return_value=(1, True))
    monkeypatch.setattr(repo, "update_identity_group", update_mock)

    result = await update_platform_identity_group("userA", "qq.custom")

    assert result is group
    update_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_group_raises_when_none_after_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = SimpleNamespace(group_id="qq.custom", builtin=False)
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    monkeypatch.setattr(
        repo,
        "get_identity_group",
        AsyncMock(side_effect=[group, None]),
    )
    monkeypatch.setattr(
        repo, "update_identity_group", AsyncMock(return_value=(1, True))
    )

    with pytest.raises(ValueError, match="Unknown identity group after update"):
        await update_platform_identity_group("userA", "qq.custom", display_name="new")


@pytest.mark.asyncio
async def test_delete_unknown_group_returns_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    monkeypatch.setattr(repo, "get_identity_group", AsyncMock(return_value=None))

    result = await delete_platform_identity_group("userA", "qq.unknown")

    assert result == (0, True)


@pytest.mark.asyncio
async def test_delete_builtin_group_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    monkeypatch.setattr(
        repo,
        "get_identity_group",
        AsyncMock(return_value=SimpleNamespace(group_id="qq.group", builtin=True)),
    )

    with pytest.raises(ValueError, match="Builtin"):
        await delete_platform_identity_group("userA", "qq.group")


@pytest.mark.asyncio
async def test_delete_group_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    monkeypatch.setattr(
        repo,
        "get_identity_group",
        AsyncMock(return_value=SimpleNamespace(group_id="qq.custom", builtin=False)),
    )
    monkeypatch.setattr(repo, "list_memberships", AsyncMock(return_value=[]))
    monkeypatch.setattr(repo, "list_grants", AsyncMock(return_value=[]))
    delete_mock = AsyncMock(return_value=(1, True))
    monkeypatch.setattr(repo, "delete_identity_group", delete_mock)

    result = await delete_platform_identity_group("userA", "qq.custom")

    assert result == (1, True)
    delete_mock.assert_awaited_once_with("qq.custom")


@pytest.mark.asyncio
async def test_delete_group_grants_in_use_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    monkeypatch.setattr(
        repo,
        "get_identity_group",
        AsyncMock(return_value=SimpleNamespace(group_id="qq.custom", builtin=False)),
    )
    monkeypatch.setattr(repo, "list_memberships", AsyncMock(return_value=[]))
    monkeypatch.setattr(repo, "list_grants", AsyncMock(return_value=[object()]))

    with pytest.raises(ValueError, match="still in use"):
        await delete_platform_identity_group("userA", "qq.custom")


@pytest.mark.asyncio
async def test_add_member_unknown_group_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    monkeypatch.setattr(repo, "get_identity_group", AsyncMock(return_value=None))

    with pytest.raises(ValueError, match="Unknown identity group"):
        await add_identity_group_member("userA", "userB", "qq.unknown")


@pytest.mark.asyncio
async def test_remove_member_calls_delete_membership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    delete_mock = AsyncMock(return_value=(1, True))
    monkeypatch.setattr(repo, "delete_membership", delete_mock)

    result = await remove_identity_group_member(
        "userA", "userB", "qq.custom", scope_type="group", scope_id="10001"
    )

    assert result == (1, True)
    delete_mock.assert_awaited_once_with(
        uid="userB",
        group_id="qq.custom",
        scope_type="group",
        scope_id="10001",
    )


@pytest.mark.asyncio
async def test_list_members_calls_list_memberships(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    memberships = [SimpleNamespace(uid="userB", group_id="qq.custom")]
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    list_mock = AsyncMock(return_value=memberships)
    monkeypatch.setattr(repo, "list_memberships", list_mock)

    result = await list_identity_group_members(
        "userA", "qq.custom", scope_type="group", scope_id="10001"
    )

    assert result is memberships
    list_mock.assert_awaited_once_with(
        group_id="qq.custom",
        scope_type="group",
        scope_id="10001",
    )


@pytest.mark.asyncio
async def test_assert_superuser_accepts_permission_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """assert_superuser resolves uid from PermissionContext actor."""
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    context = PermissionContext(
        platform_id="qq",
        adapter_id="~onebot.v11",
        account_id="42",
        uid="userA",
    )

    await assert_superuser(context)


@pytest.mark.asyncio
async def test_assert_superuser_rejects_empty_uid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty uid is rejected before querying the repository."""
    is_super = AsyncMock(return_value=True)
    monkeypatch.setattr(repo, "is_superuser", is_super)

    with pytest.raises(PermissionDeniedError):
        await assert_superuser("")

    is_super.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_group_with_permission_context_actor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """create_platform_identity_group resolves managed_by from PermissionContext."""
    created = SimpleNamespace(group_id="qq.custom")
    upsert = AsyncMock(return_value=created)
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    monkeypatch.setattr(repo, "upsert_identity_group", upsert)
    context = PermissionContext(
        platform_id="qq",
        adapter_id="~onebot.v11",
        account_id="42",
        uid="userA",
    )

    result = await create_platform_identity_group(
        context, IdentityGroupCreate("qq", "qq.custom", "自定义")
    )

    assert result is created
    assert upsert.await_args is not None
    assert upsert.await_args.kwargs["managed_by"] == "userA"
