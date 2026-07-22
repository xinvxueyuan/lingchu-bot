from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

from _lingchu_bot_contracts import MutableRuntimeSettings
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.permissions import service as service_module
from src.plugins.nonebot_plugin_lingchu_bot.permissions.service import (
    allowed_command_keys,
    bind_platform_account,
    check_permission,
    check_permission_for_context,
    platform_runtime_passthrough_enabled,
    resolve_mcp_permission,
)
from src.plugins.nonebot_plugin_lingchu_bot.permissions.types import PermissionContext
from src.plugins.nonebot_plugin_lingchu_bot.repositories import permissions as repo


@pytest.fixture
def mock_session() -> Mock:
    sess = AsyncMock()
    sess.add = MagicMock()
    sess.add_all = MagicMock()
    return sess


@pytest.fixture
def bot() -> MagicMock:
    bot = MagicMock()
    bot.adapter = MagicMock()
    bot.adapter.get_name.return_value = "OneBot V11"
    return bot


def event(user_id: int = 42) -> SimpleNamespace:
    return SimpleNamespace(
        user_id=user_id,
        group_id=10001,
        sender=SimpleNamespace(role="member"),
    )


@pytest.mark.asyncio
async def test_superuser_permission_allows_command(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
    bot: MagicMock,
) -> None:
    monkeypatch.setattr(
        repo,
        "get_user_by_platform_account",
        AsyncMock(return_value=SimpleNamespace(uid="userA")),
    )
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))

    decision = await check_permission(mock_session, "member_mute", bot, event())

    assert decision.allowed is True
    assert decision.reason == "superuser"
    assert decision.uid == "userA"


@pytest.mark.asyncio
async def test_anonymous_permission_denies_command(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
    bot: MagicMock,
) -> None:
    monkeypatch.setattr(
        repo, "get_user_by_platform_account", AsyncMock(return_value=None)
    )

    decision = await check_permission(mock_session, "member_mute", bot, event())

    assert decision.allowed is False
    assert decision.reason == "anonymous"


@pytest.mark.asyncio
async def test_group_grant_permission_allows_child_runtime_group(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
    bot: MagicMock,
) -> None:
    monkeypatch.setattr(
        repo,
        "get_user_by_platform_account",
        AsyncMock(return_value=SimpleNamespace(uid="userA")),
    )
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=False))
    monkeypatch.setattr(repo, "list_memberships", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        repo,
        "list_identity_groups",
        AsyncMock(
            return_value=[
                SimpleNamespace(group_id="qq.group", parent_group_id=None),
                SimpleNamespace(group_id="qq.group.member", parent_group_id="qq.group"),
            ]
        ),
    )
    monkeypatch.setattr(
        repo,
        "list_grants",
        AsyncMock(return_value=[SimpleNamespace(group_id="qq.group", effect="allow")]),
    )

    decision = await check_permission(mock_session, "member_mute", bot, event())

    assert decision.allowed is True
    assert decision.reason == "granted"
    assert decision.matched_groups == frozenset({"qq.group"})


@pytest.mark.asyncio
async def test_allowed_command_keys_returns_all_for_superuser(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
    bot: MagicMock,
) -> None:
    monkeypatch.setattr(
        repo,
        "get_user_by_platform_account",
        AsyncMock(return_value=SimpleNamespace(uid="userA")),
    )
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))

    keys = await allowed_command_keys(
        mock_session, bot, event(), frozenset({"member_mute", "kick_member"})
    )

    assert keys == frozenset({"member_mute", "kick_member"})


@pytest.mark.asyncio
async def test_bind_platform_account_calls_upsert_and_bind(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
) -> None:
    upsert_user_mock = AsyncMock(return_value=SimpleNamespace(uid="userA"))
    bind_mock = AsyncMock(return_value=SimpleNamespace(uid="userA", platform_id="qq"))
    monkeypatch.setattr(repo, "upsert_identity_user", upsert_user_mock)
    monkeypatch.setattr(repo, "bind_platform_account", bind_mock)

    result = await bind_platform_account(
        mock_session, "userA", "qq", 42, nickname="Alice"
    )

    assert result is bind_mock.return_value
    upsert_user_mock.assert_awaited_once_with(mock_session, "userA", "Alice")
    bind_mock.assert_awaited_once_with(
        mock_session,
        uid="userA",
        platform_id="qq",
        account_id="42",
        display_name="Alice",
    )


def _make_context(
    *,
    scope_type: str = "group",
    scope_id: str | None = "10001",
    runtime_group_ids: frozenset[str] = frozenset(),
) -> PermissionContext:
    return PermissionContext(
        platform_id="qq",
        adapter_id="~onebot.v11",
        account_id="42",
        scope_type=scope_type,
        scope_id=scope_id,
        uid="userA",
        runtime_group_ids=runtime_group_ids,
    )


@pytest.mark.asyncio
async def test_check_permission_denies_when_no_effective_groups(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
) -> None:
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=False))
    monkeypatch.setattr(repo, "list_memberships", AsyncMock(return_value=[]))
    monkeypatch.setattr(repo, "list_identity_groups", AsyncMock(return_value=[]))

    decision = await check_permission_for_context(
        mock_session, "member_mute", _make_context()
    )

    assert decision.allowed is False
    assert decision.reason == "missing_grant"
    assert decision.uid == "userA"


@pytest.mark.asyncio
async def test_resolve_mcp_permission_returns_none_without_grant(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
) -> None:
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=False))
    monkeypatch.setattr(repo, "list_memberships", AsyncMock(return_value=[]))
    monkeypatch.setattr(repo, "list_identity_groups", AsyncMock(return_value=[]))

    assert await resolve_mcp_permission(mock_session, _make_context()) is None


@pytest.mark.asyncio
async def test_resolve_mcp_permission_superuser_is_critical(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
) -> None:
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=True))

    assert await resolve_mcp_permission(mock_session, _make_context()) == "critical"


@pytest.mark.asyncio
async def test_resolve_mcp_permission_uses_highest_effective_group_level(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
) -> None:
    context = _make_context(runtime_group_ids=frozenset({"qq.runtime"}))
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=False))
    monkeypatch.setattr(
        repo,
        "list_memberships",
        AsyncMock(
            return_value=[
                SimpleNamespace(
                    group_id="qq.scoped",
                    scope_type="group",
                    scope_id="10001",
                ),
                SimpleNamespace(
                    group_id="qq.other",
                    scope_type="group",
                    scope_id="99999",
                ),
            ]
        ),
    )
    monkeypatch.setattr(
        repo,
        "list_identity_groups",
        AsyncMock(
            return_value=[
                SimpleNamespace(
                    group_id="qq.runtime",
                    parent_group_id="qq.parent",
                    mcp_permission_level="read",
                ),
                SimpleNamespace(
                    group_id="qq.parent",
                    parent_group_id=None,
                    mcp_permission_level="critical",
                ),
                SimpleNamespace(
                    group_id="qq.scoped",
                    parent_group_id=None,
                    mcp_permission_level="write_err",
                ),
                SimpleNamespace(
                    group_id="qq.other",
                    parent_group_id=None,
                    mcp_permission_level="critical",
                ),
            ]
        ),
    )

    assert await resolve_mcp_permission(mock_session, context) == "critical"


@pytest.mark.asyncio
async def test_check_permission_denies_when_no_allowed_grants(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
) -> None:
    context = _make_context(runtime_group_ids=frozenset({"qq.group.member"}))
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=False))
    monkeypatch.setattr(
        repo,
        "list_memberships",
        AsyncMock(
            return_value=[
                SimpleNamespace(
                    scope_type="group",
                    scope_id="10001",
                    group_id="qq.custom",
                )
            ]
        ),
    )
    monkeypatch.setattr(
        repo,
        "list_identity_groups",
        AsyncMock(
            return_value=[
                SimpleNamespace(group_id="qq.group.member", parent_group_id="qq.group"),
                SimpleNamespace(group_id="qq.group", parent_group_id=None),
                SimpleNamespace(group_id="qq.custom", parent_group_id=None),
            ]
        ),
    )
    monkeypatch.setattr(repo, "list_grants", AsyncMock(return_value=[]))

    decision = await check_permission_for_context(mock_session, "member_mute", context)

    assert decision.allowed is False
    assert decision.reason == "missing_grant"
    assert decision.uid == "userA"


@pytest.mark.asyncio
async def test_allowed_command_keys_non_superuser_filters(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
    bot: MagicMock,
) -> None:
    monkeypatch.setattr(
        repo,
        "get_user_by_platform_account",
        AsyncMock(return_value=SimpleNamespace(uid="userA")),
    )
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=False))
    monkeypatch.setattr(repo, "list_memberships", AsyncMock(return_value=[]))
    monkeypatch.setattr(repo, "list_identity_groups", AsyncMock(return_value=[]))
    monkeypatch.setattr(repo, "list_grants", AsyncMock(return_value=[]))

    keys = await allowed_command_keys(
        mock_session, bot, event(), frozenset({"member_mute", "kick_member"})
    )

    assert keys == frozenset()


@pytest.mark.asyncio
async def test_allowed_command_keys_non_superuser_partial_filter(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
    bot: MagicMock,
) -> None:
    """Non-superuser gets only the subset of commands they are granted."""

    async def list_grants_side_effect(*_args: object, **kwargs: object) -> list[object]:
        if kwargs.get("command_key") == "member_mute":
            return [SimpleNamespace(group_id="qq.group", effect="allow")]
        return []

    monkeypatch.setattr(
        repo,
        "get_user_by_platform_account",
        AsyncMock(return_value=SimpleNamespace(uid="userA")),
    )
    monkeypatch.setattr(repo, "is_superuser", AsyncMock(return_value=False))
    monkeypatch.setattr(repo, "list_memberships", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        repo,
        "list_identity_groups",
        AsyncMock(
            return_value=[
                SimpleNamespace(group_id="qq.group", parent_group_id=None),
                SimpleNamespace(group_id="qq.group.member", parent_group_id="qq.group"),
            ]
        ),
    )
    monkeypatch.setattr(repo, "list_grants", list_grants_side_effect)

    keys = await allowed_command_keys(
        mock_session, bot, event(), frozenset({"member_mute", "kick_member"})
    )

    assert keys == frozenset({"member_mute"})


def test_platform_runtime_passthrough_bool_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service_module,
        "get_mutable_settings",
        lambda: MutableRuntimeSettings(permission_platform_runtime_passthrough=True),
    )
    assert platform_runtime_passthrough_enabled(_make_context()) is True


def test_platform_runtime_passthrough_bool_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service_module,
        "get_mutable_settings",
        lambda: MutableRuntimeSettings(permission_platform_runtime_passthrough=False),
    )
    assert platform_runtime_passthrough_enabled(_make_context()) is False


def test_platform_runtime_passthrough_dict_platform_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service_module,
        "get_mutable_settings",
        lambda: MutableRuntimeSettings(
            permission_platform_runtime_passthrough={"qq": True}
        ),
    )
    assert platform_runtime_passthrough_enabled(_make_context()) is True


def test_platform_runtime_passthrough_dict_platform_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service_module,
        "get_mutable_settings",
        lambda: MutableRuntimeSettings(
            permission_platform_runtime_passthrough={"qq": False}
        ),
    )
    assert platform_runtime_passthrough_enabled(_make_context()) is False


def test_platform_runtime_passthrough_dict_missing_platform_defaults_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        service_module,
        "get_mutable_settings",
        lambda: MutableRuntimeSettings(
            permission_platform_runtime_passthrough={"discord": True}
        ),
    )
    assert platform_runtime_passthrough_enabled(_make_context()) is True


def test_adapter_name_returns_none_when_no_adapter() -> None:
    bot = SimpleNamespace()
    assert service_module._adapter_name(bot) is None


def test_adapter_name_returns_none_when_no_get_name() -> None:
    bot = SimpleNamespace(adapter=SimpleNamespace())
    assert service_module._adapter_name(bot) is None


def test_adapter_name_returns_none_when_get_name_raises() -> None:
    adapter = MagicMock()
    adapter.get_name.side_effect = RuntimeError("no adapter")
    bot = SimpleNamespace(adapter=adapter)
    assert service_module._adapter_name(bot) is None


def test_account_id_from_event_user_id() -> None:
    event_obj = SimpleNamespace(user_id=42)
    assert service_module._account_id(event_obj) == "42"


def test_account_id_from_data_sender() -> None:
    event_obj = SimpleNamespace(
        data=SimpleNamespace(sender=SimpleNamespace(user_id=99))
    )
    assert service_module._account_id(event_obj) == "99"


def test_account_id_returns_none_when_missing() -> None:
    event_obj = SimpleNamespace()
    assert service_module._account_id(event_obj) is None


def test_scope_from_event_group_id() -> None:
    event_obj = SimpleNamespace(group_id=10001)
    assert service_module._scope(event_obj) == ("group", "10001")


def test_scope_from_data_peer_id() -> None:
    event_obj = SimpleNamespace(data=SimpleNamespace(peer_id=20002))
    assert service_module._scope(event_obj) == ("group", "20002")


def test_scope_global_when_no_group() -> None:
    event_obj = SimpleNamespace()
    assert service_module._scope(event_obj) == ("global", None)


def test_membership_matches_global_with_none_scope_id() -> None:
    membership = SimpleNamespace(scope_type="global", scope_id=None)
    assert (
        service_module._membership_matches_context(membership, _make_context()) is True
    )


def test_membership_matches_global_with_scope_id_returns_false() -> None:
    membership = SimpleNamespace(scope_type="global", scope_id="10001")
    assert (
        service_module._membership_matches_context(membership, _make_context()) is False
    )


def test_membership_matches_group_scope_id_none() -> None:
    membership = SimpleNamespace(scope_type="group", scope_id=None)
    assert (
        service_module._membership_matches_context(membership, _make_context()) is True
    )


def test_membership_matches_group_scope_id_matches() -> None:
    membership = SimpleNamespace(scope_type="group", scope_id="10001")
    assert (
        service_module._membership_matches_context(membership, _make_context()) is True
    )


def test_membership_matches_group_scope_id_mismatch() -> None:
    membership = SimpleNamespace(scope_type="group", scope_id="99999")
    assert (
        service_module._membership_matches_context(membership, _make_context()) is False
    )


def test_membership_matches_wrong_scope_type() -> None:
    membership = SimpleNamespace(scope_type="channel", scope_id="10001")
    assert (
        service_module._membership_matches_context(membership, _make_context()) is False
    )


@pytest.mark.asyncio
async def test_with_ancestor_groups_empty(mock_session: Mock) -> None:
    result = await service_module._with_ancestor_groups(mock_session, set())
    assert result == frozenset()


@pytest.mark.asyncio
async def test_with_ancestor_groups_no_parent(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
) -> None:
    monkeypatch.setattr(
        repo,
        "list_identity_groups",
        AsyncMock(
            return_value=[SimpleNamespace(group_id="qq.custom", parent_group_id=None)]
        ),
    )
    result = await service_module._with_ancestor_groups(mock_session, {"qq.custom"})
    assert result == frozenset({"qq.custom"})


@pytest.mark.asyncio
async def test_with_ancestor_groups_parent_expansion(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
) -> None:
    monkeypatch.setattr(
        repo,
        "list_identity_groups",
        AsyncMock(
            return_value=[
                SimpleNamespace(group_id="qq.group.member", parent_group_id="qq.group"),
                SimpleNamespace(group_id="qq.group", parent_group_id=None),
            ]
        ),
    )
    result = await service_module._with_ancestor_groups(
        mock_session, {"qq.group.member"}
    )
    assert result == frozenset({"qq.group.member", "qq.group"})
