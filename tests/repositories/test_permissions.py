from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.models import (
    IdentityMembership,
    IdentityUser,
    PermissionGrant,
    PlatformAccount,
    PlatformIdentityGroup,
)
from src.plugins.nonebot_plugin_lingchu_bot.permissions.types import (
    PlatformIdentityGroupSeed,
)
from src.plugins.nonebot_plugin_lingchu_bot.repositories import permissions as repo

if TYPE_CHECKING:
    from unittest.mock import Mock

SUPERUSERS_GROUP_ID = "system.superusers"
SUPERUSERS_PLATFORM_ID = "system"
MANUAL_SOURCE = "manual"
ALLOW_EFFECT = "allow"
SEED_GROUP_CALL_COUNT = 3


def _identity_user(*, uid: str = "u1", nickname: str | None = None) -> MagicMock:
    item = MagicMock(spec=IdentityUser)
    item.uid = uid
    item.nickname = nickname or uid
    return item


def _platform_account(*, uid: str = "u1", platform_id: str = "qq") -> MagicMock:
    item = MagicMock(spec=PlatformAccount)
    item.uid = uid
    item.platform_id = platform_id
    item.account_id = "acc-1"
    item.account_type = "user"
    item.display_name = None
    return item


def _identity_group(*, group_id: str = "g1") -> MagicMock:
    item = MagicMock(spec=PlatformIdentityGroup)
    item.group_id = group_id
    item.platform_id = "qq"
    item.display_name = "Group 1"
    item.builtin = False
    item.parent_group_id = None
    item.managed_by = None
    return item


def _membership(
    *,
    uid: str = "u1",
    group_id: str = "g1",
    source: str = MANUAL_SOURCE,
) -> MagicMock:
    item = MagicMock(spec=IdentityMembership)
    item.uid = uid
    item.group_id = group_id
    item.scope_type = "global"
    item.scope_id = None
    item.source = source
    return item


def _grant(*, group_id: str = "g1", command_key: str = "cmd") -> MagicMock:
    item = MagicMock(spec=PermissionGrant)
    item.group_id = group_id
    item.command_key = command_key
    item.effect = ALLOW_EFFECT
    return item


@pytest.fixture
def mock_session() -> Mock:
    """Provide a mock AsyncSession for permissions repository tests."""
    sess = AsyncMock()
    sess.add = MagicMock()
    sess.add_all = MagicMock()
    return sess


# ---------------------------------------------------------------------------
# Identity user CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_identity_user_calls_upsert_with_uid_and_nickname(
    mock_session: Mock,
) -> None:
    user_mock = _identity_user()
    upsert_mock = AsyncMock(return_value=user_mock)

    with patch.object(repo, "upsert", upsert_mock):
        result = await repo.upsert_identity_user(
            mock_session,
            uid="u1",
            nickname="Alice",
        )

    assert result is user_mock
    assert upsert_mock.call_args.args[0] is mock_session
    assert upsert_mock.call_args.args[1] is IdentityUser
    insert_values = upsert_mock.call_args.args[2]
    assert insert_values["uid"] == "u1"
    assert insert_values["nickname"] == "Alice"
    assert upsert_mock.call_args.kwargs["conflict_fields"] == ["uid"]
    assert upsert_mock.call_args.kwargs["update_values"] == {"nickname": "Alice"}


@pytest.mark.asyncio
async def test_upsert_identity_user_defaults_nickname_to_uid(
    mock_session: Mock,
) -> None:
    user_mock = _identity_user()
    upsert_mock = AsyncMock(return_value=user_mock)

    with patch.object(repo, "upsert", upsert_mock):
        await repo.upsert_identity_user(mock_session, uid="u2")

    insert_values = upsert_mock.call_args.args[2]
    assert insert_values["nickname"] == "u2"
    assert upsert_mock.call_args.kwargs["update_values"] == {"nickname": "u2"}


# ---------------------------------------------------------------------------
# Platform account binding
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bind_platform_account_calls_upsert_with_correct_values(
    mock_session: Mock,
) -> None:
    account_mock = _platform_account()
    upsert_mock = AsyncMock(return_value=account_mock)

    with patch.object(repo, "upsert", upsert_mock):
        result = await repo.bind_platform_account(
            mock_session,
            uid="u1",
            platform_id="qq",
            account_id="acc-1",
            display_name="Alice",
        )

    assert result is account_mock
    assert upsert_mock.call_args.args[0] is mock_session
    assert upsert_mock.call_args.args[1] is PlatformAccount
    insert_values = upsert_mock.call_args.args[2]
    assert insert_values["uid"] == "u1"
    assert insert_values["platform_id"] == "qq"
    assert insert_values["account_id"] == "acc-1"
    assert insert_values["account_type"] == "user"
    assert insert_values["display_name"] == "Alice"
    assert upsert_mock.call_args.kwargs["conflict_fields"] == [
        "platform_id",
        "account_id",
    ]
    update_values = upsert_mock.call_args.kwargs["update_values"]
    assert update_values["uid"] == "u1"
    assert update_values["account_type"] == "user"
    assert update_values["display_name"] == "Alice"


@pytest.mark.asyncio
async def test_get_user_by_platform_account_returns_none_when_no_account(
    mock_session: Mock,
) -> None:
    get_one_mock = AsyncMock(return_value=None)

    with patch.object(repo, "get_one", get_one_mock):
        result = await repo.get_user_by_platform_account(
            mock_session,
            "qq",
            "acc-1",
        )

    assert result is None
    assert get_one_mock.call_args.args[0] is mock_session
    assert get_one_mock.call_args.args[1] is PlatformAccount
    assert get_one_mock.call_args.args[2] == {
        "platform_id": "qq",
        "account_id": "acc-1",
    }


@pytest.mark.asyncio
async def test_get_user_by_platform_account_returns_user_when_found(
    mock_session: Mock,
) -> None:
    account = _platform_account()
    user = _identity_user()
    get_one_mock = AsyncMock(side_effect=[account, user])

    with patch.object(repo, "get_one", get_one_mock):
        result = await repo.get_user_by_platform_account(
            mock_session,
            "qq",
            "acc-1",
        )

    assert result is user
    assert get_one_mock.call_args_list[0].args[0] is mock_session
    assert get_one_mock.call_args_list[0].args[1] is PlatformAccount
    assert get_one_mock.call_args_list[1].args[0] is mock_session
    assert get_one_mock.call_args_list[1].args[1] is IdentityUser
    assert get_one_mock.call_args_list[1].args[2] == {"uid": "u1"}


@pytest.mark.asyncio
async def test_get_platform_account_calls_get_one_with_correct_filters(
    mock_session: Mock,
) -> None:
    account = _platform_account()
    get_one_mock = AsyncMock(return_value=account)

    with patch.object(repo, "get_one", get_one_mock):
        result = await repo.get_platform_account(mock_session, "qq", "acc-1")

    assert result is account
    assert get_one_mock.call_args.args[0] is mock_session
    assert get_one_mock.call_args.args[1] is PlatformAccount
    assert get_one_mock.call_args.args[2] == {
        "platform_id": "qq",
        "account_id": "acc-1",
    }


# ---------------------------------------------------------------------------
# Identity group management
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_identity_group_calls_upsert_with_correct_values(
    mock_session: Mock,
) -> None:
    group_mock = _identity_group()
    upsert_mock = AsyncMock(return_value=group_mock)

    with patch.object(repo, "upsert", upsert_mock):
        result = await repo.upsert_identity_group(
            mock_session,
            group_id="g1",
            platform_id="qq",
            display_name="Group 1",
            mcp_permission_level="write_err",
            builtin=True,
            managed_by="plugin",
        )

    assert result is group_mock
    assert upsert_mock.call_args.args[0] is mock_session
    assert upsert_mock.call_args.args[1] is PlatformIdentityGroup
    insert_values = upsert_mock.call_args.args[2]
    assert insert_values["group_id"] == "g1"
    assert insert_values["platform_id"] == "qq"
    assert insert_values["display_name"] == "Group 1"
    assert insert_values["mcp_permission_level"] == "write_err"
    assert insert_values["builtin"] is True
    assert insert_values["managed_by"] == "plugin"
    assert upsert_mock.call_args.kwargs["conflict_fields"] == ["group_id"]
    update_values = upsert_mock.call_args.kwargs["update_values"]
    assert update_values["builtin"] is True
    assert update_values["managed_by"] == "plugin"
    assert update_values["mcp_permission_level"] == "write_err"


@pytest.mark.asyncio
async def test_upsert_identity_group_preserves_level_when_unspecified(
    mock_session: Mock,
) -> None:
    upsert_mock = AsyncMock(return_value=_identity_group())

    with patch.object(repo, "upsert", upsert_mock):
        await repo.upsert_identity_group(
            mock_session,
            group_id="builtin",
            platform_id="qq",
            display_name="Builtin",
            builtin=True,
        )

    assert upsert_mock.call_args.args[2]["mcp_permission_level"] is None
    assert "mcp_permission_level" not in upsert_mock.call_args.kwargs["update_values"]


@pytest.mark.asyncio
async def test_seed_identity_groups_creates_superusers_group_then_seeds(
    mock_session: Mock,
) -> None:
    upsert_mock = AsyncMock(return_value=_identity_group())

    seeds = [
        PlatformIdentityGroupSeed(
            group_id="admin",
            platform_id="qq",
            display_name="Admins",
        ),
        PlatformIdentityGroupSeed(
            group_id="mods",
            platform_id="qq",
            display_name="Mods",
            parent_group_id="admin",
        ),
    ]

    with patch.object(repo, "upsert", upsert_mock):
        await repo.seed_identity_groups(mock_session, seeds)

    # 1 superusers group + 2 seeds = 3 calls
    assert upsert_mock.call_count == SEED_GROUP_CALL_COUNT
    first_call = upsert_mock.call_args_list[0]
    assert first_call.args[0] is mock_session
    assert first_call.args[2]["group_id"] == SUPERUSERS_GROUP_ID
    assert first_call.args[2]["platform_id"] == SUPERUSERS_PLATFORM_ID
    assert first_call.args[2]["builtin"] is True


@pytest.mark.asyncio
async def test_get_identity_group_calls_get_one_with_group_id(
    mock_session: Mock,
) -> None:
    group = _identity_group()
    get_one_mock = AsyncMock(return_value=group)

    with patch.object(repo, "get_one", get_one_mock):
        result = await repo.get_identity_group(mock_session, "g1")

    assert result is group
    assert get_one_mock.call_args.args[0] is mock_session
    assert get_one_mock.call_args.args[1] is PlatformIdentityGroup
    assert get_one_mock.call_args.args[2] == {"group_id": "g1"}


@pytest.mark.asyncio
async def test_update_identity_group_calls_update_with_correct_args(
    mock_session: Mock,
) -> None:
    update_mock = AsyncMock(return_value=(1, True))

    with patch.object(repo, "update", update_mock):
        result = await repo.update_identity_group(
            mock_session,
            "g1",
            {"display_name": "New"},
        )

    assert result == (1, True)
    assert update_mock.call_args.args[0] is mock_session
    assert update_mock.call_args.args[1] is PlatformIdentityGroup
    assert update_mock.call_args.args[2] == {"group_id": "g1"}
    assert update_mock.call_args.args[3] == {"display_name": "New"}


@pytest.mark.asyncio
async def test_delete_identity_group_calls_delete_with_group_id(
    mock_session: Mock,
) -> None:
    delete_mock = AsyncMock(return_value=(1, True))

    with patch.object(repo, "delete", delete_mock):
        result = await repo.delete_identity_group(mock_session, "g1")

    assert result == (1, True)
    assert delete_mock.call_args.args[0] is mock_session
    assert delete_mock.call_args.args[1] is PlatformIdentityGroup
    assert delete_mock.call_args.args[2] == {"group_id": "g1"}


@pytest.mark.asyncio
async def test_list_identity_groups_without_platform_filter(
    mock_session: Mock,
) -> None:
    groups = [_identity_group(group_id="g1"), _identity_group(group_id="g2")]
    list_items_mock = AsyncMock(return_value=groups)

    with patch.object(repo, "list_items", list_items_mock):
        result = await repo.list_identity_groups(mock_session)

    assert result == groups
    assert list_items_mock.call_args.args[0] is mock_session
    assert list_items_mock.call_args.args[1] is PlatformIdentityGroup
    assert list_items_mock.call_args.args[2] is None
    assert list_items_mock.call_args.kwargs["order_by"] == ["group_id"]


@pytest.mark.asyncio
async def test_list_identity_groups_with_platform_filter(
    mock_session: Mock,
) -> None:
    groups = [_identity_group(group_id="g1")]
    list_items_mock = AsyncMock(return_value=groups)

    with patch.object(repo, "list_items", list_items_mock):
        result = await repo.list_identity_groups(mock_session, platform_id="qq")

    assert result == groups
    assert list_items_mock.call_args.args[2] == {"platform_id": "qq"}


# ---------------------------------------------------------------------------
# Membership management
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_membership_creates_new_when_not_existing(
    mock_session: Mock,
) -> None:
    membership = _membership()
    get_one_mock = AsyncMock(return_value=None)
    create_mock = AsyncMock(return_value=membership)

    with (
        patch.object(repo, "get_one", get_one_mock),
        patch.object(repo, "create", create_mock),
    ):
        result = await repo.upsert_membership(
            mock_session,
            uid="u1",
            group_id="g1",
            source="manual",
        )

    assert result is membership
    get_one_mock.assert_awaited_once()
    assert get_one_mock.call_args.args[0] is mock_session
    assert get_one_mock.call_args.args[1] is IdentityMembership
    create_mock.assert_awaited_once()
    assert create_mock.call_args.args[0] is mock_session
    assert create_mock.call_args.args[1] is IdentityMembership
    assert create_mock.call_args.kwargs == {
        "uid": "u1",
        "group_id": "g1",
        "scope_type": "global",
        "scope_id": None,
        "source": "manual",
    }


@pytest.mark.asyncio
async def test_upsert_membership_updates_source_when_existing(
    mock_session: Mock,
) -> None:
    existing = _membership(source="old")
    updated = _membership(source="new")
    get_one_mock = AsyncMock(side_effect=[existing, updated])
    update_mock = AsyncMock(return_value=(1, True))
    create_mock = AsyncMock()

    with (
        patch.object(repo, "get_one", get_one_mock),
        patch.object(repo, "update", update_mock),
        patch.object(repo, "create", create_mock),
    ):
        result = await repo.upsert_membership(
            mock_session,
            uid="u1",
            group_id="g1",
            source="new",
        )

    assert result is updated
    update_mock.assert_awaited_once()
    assert update_mock.call_args.args[0] is mock_session
    assert update_mock.call_args.args[1] is IdentityMembership
    assert update_mock.call_args.args[3] == {"source": "new"}
    create_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_membership_calls_delete_with_correct_filters(
    mock_session: Mock,
) -> None:
    delete_mock = AsyncMock(return_value=(1, True))

    with patch.object(repo, "delete", delete_mock):
        result = await repo.delete_membership(
            mock_session,
            uid="u1",
            group_id="g1",
            scope_type="global",
            scope_id=None,
        )

    assert result == (1, True)
    assert delete_mock.call_args.args[0] is mock_session
    assert delete_mock.call_args.args[1] is IdentityMembership
    assert delete_mock.call_args.args[2] == {
        "uid": "u1",
        "group_id": "g1",
        "scope_type": "global",
        "scope_id": None,
    }


@pytest.mark.asyncio
async def test_list_memberships_filters_by_uid_and_group_id(
    mock_session: Mock,
) -> None:
    memberships = [_membership()]
    list_items_mock = AsyncMock(return_value=memberships)

    with patch.object(repo, "list_items", list_items_mock):
        result = await repo.list_memberships(
            mock_session,
            uid="u1",
            group_id="g1",
        )

    assert result == memberships
    assert list_items_mock.call_args.args[0] is mock_session
    assert list_items_mock.call_args.args[1] is IdentityMembership
    assert list_items_mock.call_args.args[2] == {
        "uid": "u1",
        "group_id": "g1",
    }
    assert list_items_mock.call_args.kwargs["order_by"] == ["group_id", "uid"]


@pytest.mark.asyncio
async def test_list_memberships_with_no_filters_passes_none(
    mock_session: Mock,
) -> None:
    list_items_mock = AsyncMock(return_value=[])

    with patch.object(repo, "list_items", list_items_mock):
        await repo.list_memberships(mock_session)

    assert list_items_mock.call_args.args[2] is None


@pytest.mark.asyncio
async def test_is_superuser_returns_true_when_membership_exists(
    mock_session: Mock,
) -> None:
    membership = _membership(uid="u1", group_id=SUPERUSERS_GROUP_ID)
    get_one_mock = AsyncMock(return_value=membership)

    with patch.object(repo, "get_one", get_one_mock):
        result = await repo.is_superuser(mock_session, "u1")

    assert result is True
    assert get_one_mock.call_args.args[0] is mock_session
    assert get_one_mock.call_args.args[1] is IdentityMembership
    assert get_one_mock.call_args.args[2] == {
        "uid": "u1",
        "group_id": SUPERUSERS_GROUP_ID,
        "scope_type": "global",
        "scope_id": None,
    }


@pytest.mark.asyncio
async def test_is_superuser_returns_false_when_no_membership(
    mock_session: Mock,
) -> None:
    get_one_mock = AsyncMock(return_value=None)

    with patch.object(repo, "get_one", get_one_mock):
        result = await repo.is_superuser(mock_session, "u1")

    assert result is False


# ---------------------------------------------------------------------------
# Permission grant queries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_grant_command_calls_upsert_with_correct_values(
    mock_session: Mock,
) -> None:
    grant_mock = _grant()
    upsert_mock = AsyncMock(return_value=grant_mock)

    with patch.object(repo, "upsert", upsert_mock):
        result = await repo.grant_command(
            mock_session,
            group_id="g1",
            command_key="mute",
            effect="allow",
        )

    assert result is grant_mock
    assert upsert_mock.call_args.args[0] is mock_session
    assert upsert_mock.call_args.args[1] is PermissionGrant
    insert_values = upsert_mock.call_args.args[2]
    assert insert_values["group_id"] == "g1"
    assert insert_values["command_key"] == "mute"
    assert insert_values["effect"] == "allow"
    assert upsert_mock.call_args.kwargs["conflict_fields"] == [
        "group_id",
        "command_key",
    ]
    assert upsert_mock.call_args.kwargs["update_values"] == {"effect": "allow"}


@pytest.mark.asyncio
async def test_revoke_command_calls_delete_with_correct_filters(
    mock_session: Mock,
) -> None:
    delete_mock = AsyncMock(return_value=(1, True))

    with patch.object(repo, "delete", delete_mock):
        result = await repo.revoke_command(
            mock_session,
            group_id="g1",
            command_key="mute",
        )

    assert result == (1, True)
    assert delete_mock.call_args.args[0] is mock_session
    assert delete_mock.call_args.args[1] is PermissionGrant
    assert delete_mock.call_args.args[2] == {
        "group_id": "g1",
        "command_key": "mute",
    }


@pytest.mark.asyncio
async def test_list_grants_with_group_ids_and_command_key(
    mock_session: Mock,
) -> None:
    grants = [_grant()]
    list_items_mock = AsyncMock(return_value=grants)

    with patch.object(repo, "list_items", list_items_mock):
        result = await repo.list_grants(
            mock_session,
            group_ids=["g1", "g2"],
            command_key="mute",
        )

    assert result == grants
    assert list_items_mock.call_args.args[0] is mock_session
    assert list_items_mock.call_args.args[1] is PermissionGrant
    assert list_items_mock.call_args.args[2] == {
        "group_id": ("g1", "g2"),
        "command_key": "mute",
    }
    assert list_items_mock.call_args.kwargs["order_by"] == ["command_key"]


@pytest.mark.asyncio
async def test_list_grants_with_no_filters_passes_none(
    mock_session: Mock,
) -> None:
    list_items_mock = AsyncMock(return_value=[])

    with patch.object(repo, "list_items", list_items_mock):
        await repo.list_grants(mock_session)

    assert list_items_mock.call_args.args[2] is None
