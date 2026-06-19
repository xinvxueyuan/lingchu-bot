from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.permissions.admin import (
    PermissionDeniedError,
    add_identity_group_member,
    create_platform_identity_group,
    delete_platform_identity_group,
    update_platform_identity_group,
)
from src.plugins.nonebot_plugin_lingchu_bot.repositories import permissions as repo


@pytest.mark.asyncio
async def test_non_superuser_cannot_create_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=False))

    with pytest.raises(PermissionDeniedError):
        await create_platform_identity_group("userA", "qq", "qq.custom", "自定义")


@pytest.mark.asyncio
async def test_superuser_can_create_group(monkeypatch: pytest.MonkeyPatch) -> None:
    created = SimpleNamespace(group_id="qq.custom")
    upsert = AsyncMock(return_value=created)
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))
    monkeypatch.setattr(repo, "upsert_identity_group", upsert)

    result = await create_platform_identity_group("userA", "qq", "qq.custom", "自定义")

    assert result is created
    assert upsert.await_args is not None
    assert upsert.await_args.kwargs["builtin"] is False
    assert upsert.await_args.kwargs["managed_by"] == "userA"


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
