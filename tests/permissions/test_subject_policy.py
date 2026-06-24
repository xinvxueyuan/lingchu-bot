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
