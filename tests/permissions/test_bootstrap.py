"""Tests for permissions bootstrap superuser sync."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.menu import MENU_FEATURES
from src.plugins.nonebot_plugin_lingchu_bot.permissions import bootstrap
from src.plugins.nonebot_plugin_lingchu_bot.repositories import permissions as repo


def _superusers() -> dict[str, dict[str, str]]:
    return {"user1": {"qq": "42"}}


@pytest.mark.asyncio
async def test_sync_superusers_grants_all_menu_features() -> None:
    grant_mock = AsyncMock()

    with (
        patch.object(repo, "upsert_identity_user", AsyncMock()),
        patch.object(repo, "upsert_membership", AsyncMock()),
        patch.object(repo, "bind_platform_account", AsyncMock()),
        patch.object(repo, "grant_command", grant_mock),
    ):
        await bootstrap._sync_superusers(_superusers())

    granted_keys = {call.kwargs["command_key"] for call in grant_mock.call_args_list}
    expected_keys = {feature.command_key for feature in MENU_FEATURES}
    assert granted_keys == expected_keys
    assert grant_mock.call_count == len(MENU_FEATURES)


@pytest.mark.asyncio
async def test_sync_superusers_grants_with_superuser_group_id() -> None:
    grant_mock = AsyncMock()

    with (
        patch.object(repo, "upsert_identity_user", AsyncMock()),
        patch.object(repo, "upsert_membership", AsyncMock()),
        patch.object(repo, "bind_platform_account", AsyncMock()),
        patch.object(repo, "grant_command", grant_mock),
    ):
        await bootstrap._sync_superusers(_superusers())

    for call in grant_mock.call_args_list:
        assert call.kwargs["group_id"] == repo.SUPERUSERS_GROUP_ID


@pytest.mark.asyncio
async def test_sync_superusers_continues_after_grant_failure() -> None:
    grant_mock = AsyncMock(side_effect=RuntimeError("boom"))

    with (
        patch.object(repo, "upsert_identity_user", AsyncMock()),
        patch.object(repo, "upsert_membership", AsyncMock()),
        patch.object(repo, "bind_platform_account", AsyncMock()),
        patch.object(repo, "grant_command", grant_mock),
    ):
        await bootstrap._sync_superusers(_superusers())

    assert grant_mock.call_count == len(MENU_FEATURES)


@pytest.mark.asyncio
async def test_sync_superusers_continues_when_one_feature_fails() -> None:
    failing_key = MENU_FEATURES[0].command_key
    side_effects: list[Exception | None] = [
        RuntimeError("boom") if feature.command_key == failing_key else None
        for feature in MENU_FEATURES
    ]
    grant_mock = AsyncMock(side_effect=side_effects)

    with (
        patch.object(repo, "upsert_identity_user", AsyncMock()),
        patch.object(repo, "upsert_membership", AsyncMock()),
        patch.object(repo, "bind_platform_account", AsyncMock()),
        patch.object(repo, "grant_command", grant_mock),
    ):
        await bootstrap._sync_superusers(_superusers())

    assert grant_mock.call_count == len(MENU_FEATURES)


@pytest.mark.asyncio
async def test_sync_superusers_preserves_dependency_chain_order() -> None:
    calls: list[str] = []

    async def record_upsert_identity_user(uid: str, _nickname: str) -> None:
        calls.append(f"upsert_identity_user:{uid}")

    async def record_upsert_membership(*, uid: str, **_kwargs: object) -> None:
        calls.append(f"upsert_membership:{uid}")

    async def record_bind_platform_account(*, uid: str, **_kwargs: object) -> None:
        calls.append(f"bind_platform_account:{uid}")

    with (
        patch.object(repo, "upsert_identity_user", record_upsert_identity_user),
        patch.object(repo, "upsert_membership", record_upsert_membership),
        patch.object(repo, "bind_platform_account", record_bind_platform_account),
        patch.object(repo, "grant_command", AsyncMock()),
    ):
        await bootstrap._sync_superusers(_superusers())

    upsert_user_idx = calls.index("upsert_identity_user:user1")
    membership_idx = calls.index("upsert_membership:user1")
    bind_idx = calls.index("bind_platform_account:user1")
    assert upsert_user_idx < membership_idx < bind_idx
