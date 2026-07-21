from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.database.models import BlocklistEntry
from src.plugins.nonebot_plugin_lingchu_bot.repositories import blocklist

if TYPE_CHECKING:
    from unittest.mock import Mock

GET_ONE_GROUP_LOOKUP_COUNT = 2


def _entry(*, expires_at: datetime | None = None) -> MagicMock:
    item = MagicMock(spec=BlocklistEntry)
    item.expires_at = expires_at
    item.reason = "blocked"
    return item


@pytest.fixture
def mock_session() -> Mock:
    """Provide a mock AsyncSession for blocklist repository tests."""
    sess = AsyncMock()
    sess.add = MagicMock()
    sess.add_all = MagicMock()
    return sess


def test_scope_key_for_group_and_global() -> None:
    assert blocklist.scope_key_for("group", 123) == "123"
    assert blocklist.scope_key_for("global", 123) == "*"
    with pytest.raises(ValueError, match="group_id"):
        blocklist.scope_key_for("group", None)


def test_expires_at_from_duration_defaults_to_permanent() -> None:
    assert blocklist.expires_at_from_duration(None) is None
    assert blocklist.expires_at_from_duration(0) is None
    assert blocklist.expires_at_from_duration(-1) is None
    assert blocklist.expires_at_from_duration(60) is not None


@pytest.mark.asyncio
async def test_upsert_block_accepts_structured_request(mock_session: Mock) -> None:
    upsert_mock = AsyncMock(return_value=_entry())

    with (
        patch.object(blocklist, "upsert", upsert_mock),
        patch.object(blocklist, "_sync_blocked_policy_upsert", AsyncMock()),
    ):
        await blocklist.upsert_block(
            mock_session,
            blocklist.BlocklistUpsert(
                platform_id="qq",
                adapter_id="~onebot.v11",
                bot_id="bot-1",
                scope="group",
                group_id=123,
                user_id=456,
                operator_id=789,
                reason="bad",
                expires_at=None,
            ),
        )

    _, _, insert_values = upsert_mock.call_args.args[:3]
    assert insert_values["scope_key"] == "123"
    assert insert_values["user_id"] == "456"


@pytest.mark.asyncio
async def test_upsert_block_uses_scope_identity_and_update_values(
    mock_session: Mock,
) -> None:
    upsert_mock = AsyncMock(return_value=_entry())

    with (
        patch.object(blocklist, "upsert", upsert_mock),
        patch.object(blocklist, "_sync_blocked_policy_upsert", AsyncMock()),
    ):
        await blocklist.upsert_block(
            mock_session,
            blocklist.BlocklistUpsert(
                platform_id="qq",
                adapter_id="~onebot.v11",
                bot_id="bot-1",
                scope="group",
                group_id=123,
                user_id=456,
                operator_id=789,
                reason="bad",
                expires_at=None,
            ),
        )

    _, _, insert_values = upsert_mock.call_args.args[:3]
    assert insert_values["scope"] == "group"
    assert insert_values["scope_key"] == "123"
    assert insert_values["group_id"] == "123"
    assert insert_values["user_id"] == "456"
    assert upsert_mock.call_args.kwargs["conflict_fields"] == [
        "platform_id",
        "adapter_id",
        "protocol_id",
        "bot_id",
        "scope",
        "scope_key",
        "user_id",
    ]
    assert upsert_mock.call_args.kwargs["update_values"]["reason"] == "bad"


@pytest.mark.asyncio
async def test_upsert_block_passes_protocol_id_through_to_upsert(
    mock_session: Mock,
) -> None:
    upsert_mock = AsyncMock(return_value=_entry())

    with (
        patch.object(blocklist, "upsert", upsert_mock),
        patch.object(blocklist, "_sync_blocked_policy_upsert", AsyncMock()),
    ):
        await blocklist.upsert_block(
            mock_session,
            blocklist.BlocklistUpsert(
                platform_id="qq",
                adapter_id="~onebot.v11",
                protocol_id="napcat",
                bot_id="bot-1",
                scope="group",
                group_id=123,
                user_id=456,
                operator_id=789,
                reason="bad",
                expires_at=None,
            ),
        )

    _, _, insert_values = upsert_mock.call_args.args[:3]
    assert insert_values["protocol_id"] == "napcat"
    assert "protocol_id" in upsert_mock.call_args.kwargs["conflict_fields"]
    assert upsert_mock.call_args.kwargs["update_values"]["protocol_id"] == "napcat"


@pytest.mark.asyncio
async def test_upsert_block_defaults_protocol_id_to_none(mock_session: Mock) -> None:
    upsert_mock = AsyncMock(return_value=_entry())

    with (
        patch.object(blocklist, "upsert", upsert_mock),
        patch.object(blocklist, "_sync_blocked_policy_upsert", AsyncMock()),
    ):
        await blocklist.upsert_block(
            mock_session,
            blocklist.BlocklistUpsert(
                platform_id="qq",
                adapter_id="~onebot.v11",
                bot_id="bot-1",
                scope="group",
                group_id=123,
                user_id=456,
                operator_id=789,
                reason="bad",
                expires_at=None,
            ),
        )

    _, _, insert_values = upsert_mock.call_args.args[:3]
    assert insert_values["protocol_id"] is None
    assert upsert_mock.call_args.kwargs["update_values"]["protocol_id"] is None


@pytest.mark.asyncio
async def test_upsert_block_preserves_none_operator_id(mock_session: Mock) -> None:
    upsert_mock = AsyncMock(return_value=_entry())

    with (
        patch.object(blocklist, "upsert", upsert_mock),
        patch.object(blocklist, "_sync_blocked_policy_upsert", AsyncMock()),
    ):
        await blocklist.upsert_block(
            mock_session,
            blocklist.BlocklistUpsert(
                platform_id="qq",
                adapter_id="~onebot.v11",
                bot_id="bot-1",
                scope="group",
                group_id=123,
                user_id=456,
                operator_id=None,
                reason="bad",
                expires_at=None,
            ),
        )

    _, _, insert_values = upsert_mock.call_args.args[:3]
    assert insert_values["operator_id"] is None
    assert upsert_mock.call_args.kwargs["update_values"]["operator_id"] is None


@pytest.mark.asyncio
async def test_upsert_block_syncs_blocked_subject_policy(mock_session: Mock) -> None:
    upsert_mock = AsyncMock(return_value=_entry())
    sync_mock = AsyncMock()
    request = blocklist.BlocklistUpsert(
        platform_id="qq",
        adapter_id="~onebot.v11",
        protocol_id="napcat",
        bot_id="bot-1",
        scope="group",
        group_id=123,
        user_id=456,
        operator_id=789,
        reason="bad",
        expires_at=None,
    )

    with (
        patch.object(blocklist, "upsert", upsert_mock),
        patch.object(blocklist, "_sync_blocked_policy_upsert", sync_mock),
    ):
        await blocklist.upsert_block(mock_session, request)

    sync_mock.assert_awaited_once_with(mock_session, request)


@pytest.mark.asyncio
async def test_remove_and_clear_use_expected_scope_filters(
    mock_session: Mock,
) -> None:
    delete_mock = AsyncMock(return_value=(1, True))

    with (
        patch.object(blocklist, "delete", delete_mock),
        patch.object(blocklist, "_sync_blocked_policy_remove", AsyncMock()),
        patch.object(blocklist, "_sync_blocked_policy_clear", AsyncMock()),
    ):
        await blocklist.remove_block(
            mock_session,
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            scope="global",
            group_id=123,
            user_id=456,
        )
        await blocklist.clear_blocklist(
            mock_session,
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            scope="group",
            group_id=123,
        )

    first_filters = delete_mock.call_args_list[0].args[2]
    second_filters = delete_mock.call_args_list[1].args[2]
    assert first_filters["scope"] == "global"
    assert first_filters["scope_key"] == "*"
    assert first_filters["user_id"] == "456"
    assert second_filters["scope"] == "group"
    assert second_filters["scope_key"] == "123"
    assert "user_id" not in second_filters


@pytest.mark.asyncio
async def test_remove_block_includes_protocol_id_filter_when_provided(
    mock_session: Mock,
) -> None:
    delete_mock = AsyncMock(return_value=(1, True))

    with (
        patch.object(blocklist, "delete", delete_mock),
        patch.object(blocklist, "_sync_blocked_policy_remove", AsyncMock()),
    ):
        await blocklist.remove_block(
            mock_session,
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id="napcat",
            bot_id="bot-1",
            scope="group",
            group_id=123,
            user_id=456,
        )

    filters = delete_mock.call_args.args[2]
    assert filters["protocol_id"] == "napcat"


@pytest.mark.asyncio
async def test_find_active_block_prefers_global_entry(mock_session: Mock) -> None:
    get_one_mock = AsyncMock(return_value=_entry())

    with patch.object(blocklist, "get_one", get_one_mock):
        result = await blocklist.find_active_block(
            mock_session,
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            group_id=123,
            user_id=456,
        )

    assert result is not None
    assert get_one_mock.await_count == 1
    assert get_one_mock.call_args.args[2]["scope"] == "global"


@pytest.mark.asyncio
async def test_find_active_block_falls_back_to_group_entry(
    mock_session: Mock,
) -> None:
    get_one_mock = AsyncMock(side_effect=[None, _entry()])

    with patch.object(blocklist, "get_one", get_one_mock):
        result = await blocklist.find_active_block(
            mock_session,
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            group_id=123,
            user_id=456,
        )

    assert result is not None
    assert get_one_mock.await_count == GET_ONE_GROUP_LOOKUP_COUNT
    assert get_one_mock.call_args_list[1].args[2]["scope"] == "group"


@pytest.mark.asyncio
async def test_find_active_block_lazily_deletes_expired_entries(
    mock_session: Mock,
) -> None:
    expired = _entry(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    get_one_mock = AsyncMock(side_effect=[expired, None])
    delete_mock = AsyncMock(return_value=(1, True))

    with (
        patch.object(blocklist, "get_one", get_one_mock),
        patch.object(blocklist, "delete", delete_mock),
    ):
        result = await blocklist.find_active_block(
            mock_session,
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            group_id=123,
            user_id=456,
        )

    assert result is None
    delete_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_clear_blocklist_includes_protocol_id_filter_when_provided(
    mock_session: Mock,
) -> None:
    delete_mock = AsyncMock(return_value=(1, True))

    with (
        patch.object(blocklist, "delete", delete_mock),
        patch.object(blocklist, "_sync_blocked_policy_clear", AsyncMock()),
    ):
        await blocklist.clear_blocklist(
            mock_session,
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id="napcat",
            bot_id="bot-1",
            scope="group",
            group_id=123,
        )

    filters = delete_mock.call_args.args[2]
    assert filters["protocol_id"] == "napcat"


@pytest.mark.asyncio
async def test_find_active_block_passes_protocol_id_and_returns_unexpired_entry() -> (
    None
):
    future = datetime.now(UTC) + timedelta(seconds=60)
    entry = _entry(expires_at=future)
    get_one_mock = AsyncMock(return_value=entry)

    with patch.object(blocklist, "get_one", get_one_mock):
        result = await blocklist.find_active_block(
            MagicMock(),
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id="napcat",
            bot_id="bot-1",
            group_id=123,
            user_id=456,
        )

    assert result is entry
    assert get_one_mock.call_args_list[0].args[2]["protocol_id"] == "napcat"


@pytest.mark.asyncio
async def test_cleanup_expired_blocks_delegates_to_delete_with_conditions(
    mock_session: Mock,
) -> None:
    delete_mock = AsyncMock(return_value=(3, True))

    with patch.object(blocklist, "delete", delete_mock):
        result = await blocklist.cleanup_expired_blocks(mock_session)

    assert result == (3, True)
    delete_mock.assert_awaited_once()
    kwargs = delete_mock.call_args.kwargs
    assert "conditions" in kwargs
    assert len(kwargs["conditions"]) == 2


def test_active_block_condition_returns_or_clause() -> None:
    condition = blocklist.active_block_condition()

    assert condition is not None


@pytest.mark.asyncio
async def test_sync_blocked_policy_upsert_invokes_upsert_subject_policy(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
) -> None:
    from src.plugins.nonebot_plugin_lingchu_bot.permissions import subject_policy

    upsert_mock = AsyncMock()
    monkeypatch.setattr(subject_policy, "upsert_subject_policy", upsert_mock)

    request = blocklist.BlocklistUpsert(
        platform_id="qq",
        adapter_id="~onebot.v11",
        protocol_id="napcat",
        bot_id="bot-1",
        scope="group",
        group_id=123,
        user_id=456,
        operator_id=789,
        reason="bad",
        expires_at=None,
    )

    await blocklist._sync_blocked_policy_upsert(mock_session, request)

    upsert_mock.assert_awaited_once()
    assert upsert_mock.await_args is not None
    assert upsert_mock.await_args.args[0] is mock_session
    call_arg = upsert_mock.await_args.args[1]
    assert call_arg.policy_type == "blocked"
    assert call_arg.platform_id == "qq"
    assert call_arg.protocol_id == "napcat"
    assert call_arg.user_id == 456


@pytest.mark.asyncio
async def test_sync_blocked_policy_remove_invokes_remove_subject_policy(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
) -> None:
    from src.plugins.nonebot_plugin_lingchu_bot.permissions import subject_policy

    remove_mock = AsyncMock()
    monkeypatch.setattr(subject_policy, "remove_subject_policy", remove_mock)

    await blocklist._sync_blocked_policy_remove(
        mock_session,
        platform_id="qq",
        adapter_id="~onebot.v11",
        protocol_id="napcat",
        bot_id="bot-1",
        scope="group",
        group_id=123,
        user_id=456,
    )

    remove_mock.assert_awaited_once()
    assert remove_mock.await_args is not None
    assert remove_mock.await_args.args[0] is mock_session
    kwargs = remove_mock.await_args.kwargs
    assert kwargs["policy_type"] == "blocked"
    assert kwargs["platform_id"] == "qq"
    assert kwargs["protocol_id"] == "napcat"


@pytest.mark.asyncio
async def test_sync_blocked_policy_clear_invokes_clear_subject_policy(
    monkeypatch: pytest.MonkeyPatch,
    mock_session: Mock,
) -> None:
    from src.plugins.nonebot_plugin_lingchu_bot.permissions import subject_policy

    clear_mock = AsyncMock()
    monkeypatch.setattr(subject_policy, "clear_subject_policy", clear_mock)

    await blocklist._sync_blocked_policy_clear(
        mock_session,
        platform_id="qq",
        adapter_id="~onebot.v11",
        protocol_id="napcat",
        bot_id="bot-1",
        scope="group",
        group_id=123,
    )

    clear_mock.assert_awaited_once()
    assert clear_mock.await_args is not None
    assert clear_mock.await_args.args[0] is mock_session
    kwargs = clear_mock.await_args.kwargs
    assert kwargs["policy_type"] == "blocked"
    assert kwargs["platform_id"] == "qq"
    assert kwargs["protocol_id"] == "napcat"
