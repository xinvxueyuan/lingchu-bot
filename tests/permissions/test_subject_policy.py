from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.plugins.nonebot_plugin_lingchu_bot.permissions import subject_policy


def _entry(*, expires_at: datetime | None = None) -> MagicMock:
    item = MagicMock()
    item.expires_at = expires_at
    item.reason = "protected"
    return item


@pytest.mark.asyncio
async def test_protected_subject_prefers_global_scope() -> None:
    get_one_mock = AsyncMock(return_value=_entry())

    with patch.object(subject_policy, "get_one", get_one_mock):
        result = await subject_policy.find_active_subject_policy(
            policy_type="protected",
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            group_id=123,
            user_id=456,
        )

    assert result is not None
    assert get_one_mock.await_count == 1
    assert get_one_mock.call_args.args[1]["policy_type"] == "protected"
    assert get_one_mock.call_args.args[1]["scope"] == "global"


@pytest.mark.asyncio
async def test_expired_subject_policy_is_deleted() -> None:
    expired = _entry(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    get_one_mock = AsyncMock(side_effect=[expired, None])
    delete_mock = AsyncMock(return_value=(1, True))

    with (
        patch.object(subject_policy, "get_one", get_one_mock),
        patch.object(subject_policy, "delete", delete_mock),
    ):
        result = await subject_policy.find_active_subject_policy(
            policy_type="protected",
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            group_id=123,
            user_id=456,
        )

    assert result is None
    delete_mock.assert_awaited_once()


def test_expires_at_from_duration_none_returns_none() -> None:
    assert subject_policy.expires_at_from_duration(None) is None


def test_expires_at_from_duration_zero_returns_none() -> None:
    assert subject_policy.expires_at_from_duration(0) is None


def test_expires_at_from_duration_negative_returns_none() -> None:
    assert subject_policy.expires_at_from_duration(-10) is None


def test_expires_at_from_duration_positive_returns_future() -> None:
    before = datetime.now(UTC)
    result = subject_policy.expires_at_from_duration(60)
    after = datetime.now(UTC)

    assert result is not None
    assert before + timedelta(seconds=60) <= result <= after + timedelta(seconds=60)


@pytest.mark.asyncio
async def test_upsert_subject_policy_global_scope_without_operator() -> None:
    entry = MagicMock()
    upsert_mock = AsyncMock(return_value=entry)
    request = subject_policy.SubjectPolicyUpsert(
        policy_type="blocked",
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="bot-1",
        scope="global",
        group_id=None,
        user_id=456,
        operator_id=None,
        reason=None,
        expires_at=None,
    )

    with patch.object(subject_policy, "upsert", upsert_mock):
        result = await subject_policy.upsert_subject_policy(request)

    assert result is entry
    assert upsert_mock.await_args is not None
    values = upsert_mock.await_args.args[1]
    assert values["scope"] == "global"
    assert values["scope_key"] == "*"
    assert values["group_id"] is None
    assert values["user_id"] == "456"
    assert values["operator_id"] is None
    assert values["reason"] is None
    assert values["protocol_id"] is None
    assert upsert_mock.await_args.kwargs["conflict_fields"] == [
        "policy_type",
        "platform_id",
        "adapter_id",
        "protocol_id",
        "bot_id",
        "scope",
        "scope_key",
        "user_id",
    ]


@pytest.mark.asyncio
async def test_upsert_subject_policy_group_scope_with_operator() -> None:
    entry = MagicMock()
    upsert_mock = AsyncMock(return_value=entry)
    expires = datetime.now(UTC) + timedelta(seconds=120)
    request = subject_policy.SubjectPolicyUpsert(
        policy_type="protected",
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id="bot-1",
        scope="group",
        group_id=123,
        user_id=456,
        operator_id=789,
        reason="vip",
        expires_at=expires,
        protocol_id="default",
    )

    with patch.object(subject_policy, "upsert", upsert_mock):
        result = await subject_policy.upsert_subject_policy(request)

    assert result is entry
    assert upsert_mock.await_args is not None
    values = upsert_mock.await_args.args[1]
    assert values["scope"] == "group"
    assert values["scope_key"] == "123"
    assert values["group_id"] == "123"
    assert values["user_id"] == "456"
    assert values["operator_id"] == "789"
    assert values["protocol_id"] == "default"
    assert values["reason"] == "vip"
    assert values["expires_at"] == expires
    assert upsert_mock.await_args.kwargs["update_values"]["reason"] == "vip"
    assert upsert_mock.await_args.kwargs["update_values"]["expires_at"] == expires


@pytest.mark.asyncio
async def test_remove_subject_policy_with_protocol_id() -> None:
    delete_mock = AsyncMock(return_value=(1, True))

    with patch.object(subject_policy, "delete", delete_mock):
        result = await subject_policy.remove_subject_policy(
            policy_type="blocked",
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id="default",
            bot_id="bot-1",
            scope="group",
            group_id=123,
            user_id=456,
        )

    assert result == (1, True)
    assert delete_mock.await_args is not None
    filters = delete_mock.await_args.args[1]
    assert filters["protocol_id"] == "default"
    assert filters["scope"] == "group"
    assert filters["scope_key"] == "123"
    assert filters["user_id"] == "456"
    assert filters["policy_type"] == "blocked"


@pytest.mark.asyncio
async def test_remove_subject_policy_without_protocol_id() -> None:
    delete_mock = AsyncMock(return_value=(0, True))

    with patch.object(subject_policy, "delete", delete_mock):
        result = await subject_policy.remove_subject_policy(
            policy_type="blocked",
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            scope="global",
            group_id=None,
            user_id=456,
        )

    assert result == (0, True)
    assert delete_mock.await_args is not None
    filters = delete_mock.await_args.args[1]
    assert "protocol_id" not in filters
    assert filters["scope_key"] == "*"


@pytest.mark.asyncio
async def test_clear_subject_policy_with_protocol_id() -> None:
    delete_mock = AsyncMock(return_value=(2, True))

    with patch.object(subject_policy, "delete", delete_mock):
        result = await subject_policy.clear_subject_policy(
            policy_type="blocked",
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id="napcat",
            bot_id="bot-1",
            scope="group",
            group_id=123,
        )

    assert result == (2, True)
    assert delete_mock.await_args is not None
    filters = delete_mock.await_args.args[1]
    assert filters["protocol_id"] == "napcat"
    assert "user_id" not in filters
    assert filters["scope_key"] == "123"


@pytest.mark.asyncio
async def test_clear_subject_policy_without_protocol_id() -> None:
    delete_mock = AsyncMock(return_value=(0, False))

    with patch.object(subject_policy, "delete", delete_mock):
        result = await subject_policy.clear_subject_policy(
            policy_type="protected",
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            scope="global",
            group_id=None,
        )

    assert result == (0, False)
    assert delete_mock.await_args is not None
    filters = delete_mock.await_args.args[1]
    assert "protocol_id" not in filters
    assert "user_id" not in filters
    assert filters["scope_key"] == "*"


@pytest.mark.asyncio
async def test_find_active_subject_policy_with_protocol_id() -> None:
    entry = _entry()
    get_one_mock = AsyncMock(return_value=entry)

    with patch.object(subject_policy, "get_one", get_one_mock):
        result = await subject_policy.find_active_subject_policy(
            policy_type="protected",
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id="default",
            bot_id="bot-1",
            group_id=123,
            user_id=456,
        )

    assert result is entry
    assert get_one_mock.await_args is not None
    filters = get_one_mock.await_args.args[1]
    assert filters["protocol_id"] == "default"


@pytest.mark.asyncio
async def test_find_active_subject_policy_falls_back_to_group_scope() -> None:
    group_entry = _entry()
    get_one_mock = AsyncMock(side_effect=[None, group_entry])

    with patch.object(subject_policy, "get_one", get_one_mock):
        result = await subject_policy.find_active_subject_policy(
            policy_type="protected",
            platform_id="qq",
            adapter_id="~onebot.v11",
            bot_id="bot-1",
            group_id=123,
            user_id=456,
        )

    assert result is group_entry
    assert get_one_mock.await_count == 2
    second_filters = get_one_mock.await_args_list[1].args[1]
    assert second_filters["scope"] == "group"
    assert second_filters["scope_key"] == "123"


@pytest.mark.asyncio
async def test_find_active_subject_policy_with_protocol_id_group_scope() -> None:
    """protocol_id filter is applied in the group-scope fallback path too."""
    group_entry = _entry()
    get_one_mock = AsyncMock(side_effect=[None, group_entry])

    with patch.object(subject_policy, "get_one", get_one_mock):
        result = await subject_policy.find_active_subject_policy(
            policy_type="protected",
            platform_id="qq",
            adapter_id="~onebot.v11",
            protocol_id="napcat",
            bot_id="bot-1",
            group_id=123,
            user_id=456,
        )

    assert result is group_entry
    assert get_one_mock.await_count == 2
    global_filters = get_one_mock.await_args_list[0].args[1]
    group_filters = get_one_mock.await_args_list[1].args[1]
    assert global_filters["protocol_id"] == "napcat"
    assert group_filters["protocol_id"] == "napcat"


def test_active_subject_policy_condition_returns_clause() -> None:
    condition = subject_policy.active_subject_policy_condition()

    assert condition is not None
