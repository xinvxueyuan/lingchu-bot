"""Tests for permissions bootstrap superuser sync."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.menu import MENU_FEATURES
from src.plugins.nonebot_plugin_lingchu_bot.permissions import bootstrap
from src.plugins.nonebot_plugin_lingchu_bot.permissions.bootstrap import (
    PermissionConfigError,
)
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


# --- _resolve_superusers_config ---


def test_resolve_superusers_config_raises_when_superusers_is_none() -> None:
    """lingchu_superusers 为 None 时抛出 PermissionConfigError。"""
    mock_config = SimpleNamespace(lingchu_superusers=None)
    with (
        patch.object(bootstrap, "get_runtime_config", return_value=mock_config),
        pytest.raises(
            PermissionConfigError,
            match="LINGCHU_SUPERUSERS is required",
        ),
    ):
        bootstrap._resolve_superusers_config()


def test_resolve_superusers_config_normalizes_int_account_ids_to_str() -> None:
    """Int 类型的 account_id 在解析阶段被转为 str。"""
    raw: dict[str, dict[str, str | int]] = {"user1": {"qq": 42}}
    mock_config = SimpleNamespace(lingchu_superusers=raw)
    with patch.object(bootstrap, "get_runtime_config", return_value=mock_config):
        result = bootstrap._resolve_superusers_config()
    assert result == {"user1": {"qq": "42"}}


# --- _normalize_superusers_mapping ---


def test_normalize_superusers_mapping_converts_int_account_id_to_str() -> None:
    """Int account_id 被转成 str。"""
    raw: dict[str, dict[str, str | int]] = {"123": {"qq": 42}}
    result = bootstrap._normalize_superusers_mapping(raw)
    assert result == {"123": {"qq": "42"}}


def test_normalize_superusers_mapping_preserves_str_values() -> None:
    """Str 输入保持不变（键和值都已是 str）。"""
    raw: dict[str, dict[str, str | int]] = {"user1": {"qq": "42"}}
    result = bootstrap._normalize_superusers_mapping(raw)
    assert result == {"user1": {"qq": "42"}}


def test_normalize_superusers_mapping_handles_multiple_platforms() -> None:
    """多平台、多 UID 输入被完整规范化。"""
    raw: dict[str, dict[str, str | int]] = {
        "user1": {"qq": 42, "telegram": "tg-1"},
        "user2": {"qq": "43"},
    }
    result = bootstrap._normalize_superusers_mapping(raw)
    assert result == {
        "user1": {"qq": "42", "telegram": "tg-1"},
        "user2": {"qq": "43"},
    }


# --- _validate_superusers ---


def test_validate_superusers_raises_when_mapping_empty() -> None:
    """空 mapping 抛出 PermissionConfigError。"""
    with pytest.raises(
        PermissionConfigError,
        match="LINGCHU_SUPERUSERS cannot be empty",
    ):
        bootstrap._validate_superusers({})


def test_validate_superusers_raises_when_uid_is_empty_string() -> None:
    """UID 为空字符串时抛出 PermissionConfigError。"""
    with pytest.raises(
        PermissionConfigError,
        match="SUPERUSERS UID cannot be empty",
    ):
        bootstrap._validate_superusers({"": {"qq": "42"}})


def test_validate_superusers_raises_when_uid_is_only_whitespace() -> None:
    """UID 仅含空白字符时同样抛出 PermissionConfigError。"""
    with pytest.raises(
        PermissionConfigError,
        match="SUPERUSERS UID cannot be empty",
    ):
        bootstrap._validate_superusers({"   ": {"qq": "42"}})


def test_validate_superusers_raises_when_accounts_empty() -> None:
    """Accounts 为空 dict 时抛出带 UID 信息的 PermissionConfigError。"""
    with pytest.raises(
        PermissionConfigError,
        match=r"SUPERUSERS UID 'user1' has no platform accounts",
    ):
        bootstrap._validate_superusers({"user1": {}})


def test_validate_superusers_raises_when_platform_unknown() -> None:
    """未知 platform_id 抛出 PermissionConfigError。"""
    with pytest.raises(
        PermissionConfigError,
        match=r"Unknown SUPERUSERS platform: telegram",
    ):
        bootstrap._validate_superusers({"user1": {"telegram": "42"}})


def test_validate_superusers_raises_on_duplicate_account_binding() -> None:
    """重复 (platform_id, account_id) 组合抛出 PermissionConfigError。"""
    superusers = {"user1": {"qq": "42"}, "user2": {"qq": "42"}}
    with pytest.raises(
        PermissionConfigError,
        match=r"Duplicate SUPERUSERS account binding: qq/42",
    ):
        bootstrap._validate_superusers(superusers)


def test_validate_superusers_accepts_valid_mapping() -> None:
    """合法 mapping 不抛异常（QQ 平台 + 正整数 account_id）。"""
    # Should not raise.
    bootstrap._validate_superusers({"user1": {"qq": "42"}})


def test_validate_superusers_accepts_multiple_distinct_accounts() -> None:
    """同一平台下不同 account_id 不视为重复。"""
    # Should not raise.
    bootstrap._validate_superusers(
        {"user1": {"qq": "42"}, "user2": {"qq": "43"}},
    )


# --- _validate_platform_account_id ---


def test_validate_platform_account_id_raises_when_value_empty() -> None:
    """空 account_id 抛出 PermissionConfigError。"""
    with pytest.raises(
        PermissionConfigError,
        match=r"qq SUPERUSERS account cannot be empty",
    ):
        bootstrap._validate_platform_account_id("qq", "")


def test_validate_platform_account_id_raises_when_value_is_whitespace() -> None:
    """仅含空白的 account_id 在 strip 后同样抛出 PermissionConfigError。"""
    with pytest.raises(
        PermissionConfigError,
        match=r"qq SUPERUSERS account cannot be empty",
    ):
        bootstrap._validate_platform_account_id("qq", "   ")


def test_validate_platform_account_id_raises_when_qq_account_not_int() -> None:
    """QQ account_id 非整数抛出 PermissionConfigError。"""
    with pytest.raises(
        PermissionConfigError,
        match=r"QQ SUPERUSERS account must be a positive int",
    ):
        bootstrap._validate_platform_account_id("qq", "abc")


def test_validate_platform_account_id_raises_when_qq_account_is_zero() -> None:
    """QQ account_id 为 0 抛出 PermissionConfigError。"""
    with pytest.raises(
        PermissionConfigError,
        match=r"QQ SUPERUSERS account must be a positive int",
    ):
        bootstrap._validate_platform_account_id("qq", "0")


def test_validate_platform_account_id_raises_when_qq_account_is_negative() -> None:
    """QQ account_id 为负数抛出 PermissionConfigError。"""
    with pytest.raises(
        PermissionConfigError,
        match=r"QQ SUPERUSERS account must be a positive int",
    ):
        bootstrap._validate_platform_account_id("qq", "-5")


def test_validate_platform_account_id_returns_str_for_valid_qq_account() -> None:
    """合法 QQ account_id 返回 str 形式。"""
    assert bootstrap._validate_platform_account_id("qq", "42") == "42"


def test_validate_platform_account_id_returns_stripped_str_for_non_qq_platform() -> (
    None
):
    """非 QQ 平台走默认分支，返回 strip 后的 str（覆盖行 94）。"""
    result = bootstrap._validate_platform_account_id("telegram", "  abc123  ")
    assert result == "abc123"


# --- validate_and_seed_permission_system ---


@pytest.mark.asyncio
async def test_validate_and_seed_permission_system_calls_seed_and_sync() -> None:
    """成功路径：调用 seed_identity_groups 与 _sync_superusers。"""
    superusers = {"user1": {"qq": "42"}}
    with (
        patch.object(bootstrap, "_resolve_superusers_config", return_value=superusers),
        patch.object(bootstrap, "_sync_superusers", AsyncMock()) as sync_mock,
        patch.object(repo, "seed_identity_groups", AsyncMock()) as seed_mock,
    ):
        await bootstrap.validate_and_seed_permission_system()

    seed_mock.assert_awaited_once()
    sync_mock.assert_awaited_once_with(superusers)


@pytest.mark.asyncio
async def test_validate_and_seed_permission_system_stops_on_config_error() -> None:
    """_resolve_superusers_config 抛错时不再继续 seed/sync。"""
    with (
        patch.object(
            bootstrap,
            "_resolve_superusers_config",
            side_effect=PermissionConfigError("LINGCHU_SUPERUSERS is required"),
        ),
        patch.object(bootstrap, "_sync_superusers", AsyncMock()) as sync_mock,
        patch.object(repo, "seed_identity_groups", AsyncMock()) as seed_mock,
        pytest.raises(
            PermissionConfigError,
            match="LINGCHU_SUPERUSERS is required",
        ),
    ):
        await bootstrap.validate_and_seed_permission_system()

    seed_mock.assert_not_awaited()
    sync_mock.assert_not_awaited()
