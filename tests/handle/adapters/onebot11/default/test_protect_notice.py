"""测试白名单受保护用户被禁言后的自动恢复通知监听。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from nonebot.adapters.onebot.v11 import Bot as OneBot11Bot
from nonebot.adapters.onebot.v11.exception import ActionFailed as OneBot11ActionFailed
import pytest

from src.plugins.nonebot_plugin_lingchu_bot.handle.qq.adapters.onebot11.default import (
    protect_notice as module,
)

_PROTECTED_USER_ID = 100001
_GROUP_ID = 200001
_OPERATOR_ID = 300001
_BOT_ID = "123456789"


def _ban_event(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "sub_type": "ban",
        "duration": 60,
        "user_id": _PROTECTED_USER_ID,
        "group_id": _GROUP_ID,
        "operator_id": _OPERATOR_ID,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _bot() -> MagicMock:
    bot = MagicMock(spec=OneBot11Bot)
    bot.self_id = _BOT_ID
    bot.get_group_member_info = AsyncMock(return_value={})
    bot.set_group_ban = AsyncMock()
    return bot


@pytest.fixture
def mock_session() -> Mock:
    return Mock()


@pytest.fixture(autouse=True)
def _mock_audit():
    """避免审计记录触发后台任务。"""
    with patch.object(module, "_fire_protect_restore_audit", new=MagicMock()):
        yield


@pytest.mark.asyncio
async def test_restores_protected_user_muted_by_admin(
    mock_session: Mock,
) -> None:
    """普通管理员禁言受保护用户 → 自动解禁。"""
    bot = _bot()
    event = _ban_event()

    with (
        patch.object(
            module,
            "find_active_subject_policy",
            new=AsyncMock(return_value=SimpleNamespace(group_id=_GROUP_ID)),
        ),
        patch.object(
            module,
            "operator_is_superuser_onebot11",
            new=AsyncMock(return_value=False),
        ),
        patch.object(
            module, "_is_whole_group_muted", new=AsyncMock(return_value=False)
        ),
        patch.object(
            module, "_fire_protect_restore_audit", new=MagicMock()
        ) as audit_mock,
    ):
        await module.handle_group_ban_notice(bot, event, mock_session)

    bot.set_group_ban.assert_awaited_once_with(
        group_id=_GROUP_ID,
        user_id=_PROTECTED_USER_ID,
        duration=0,
    )
    audit_mock.assert_called_once()


@pytest.mark.asyncio
async def test_policy_lookup_uses_protected_scope(mock_session: Mock) -> None:
    """策略查询使用 protected 类型与群/用户维度。"""
    bot = _bot()
    event = _ban_event()
    find_mock = AsyncMock(return_value=SimpleNamespace())

    with (
        patch.object(module, "find_active_subject_policy", find_mock),
        patch.object(
            module, "operator_is_superuser_onebot11", AsyncMock(return_value=False)
        ),
        patch.object(
            module, "_is_whole_group_muted", new=AsyncMock(return_value=False)
        ),
    ):
        await module.handle_group_ban_notice(bot, event, mock_session)

    find_mock.assert_awaited_once_with(
        mock_session,
        policy_type="protected",
        platform_id="qq",
        adapter_id="~onebot.v11",
        bot_id=_BOT_ID,
        group_id=_GROUP_ID,
        user_id=_PROTECTED_USER_ID,
    )


@pytest.mark.asyncio
async def test_ignores_lift_ban(mock_session: Mock) -> None:
    """解禁事件（lift_ban）不触发恢复。"""
    bot = _bot()
    event = _ban_event(sub_type="lift_ban", duration=0)

    with patch.object(module, "find_active_subject_policy", AsyncMock()) as find_mock:
        await module.handle_group_ban_notice(bot, event, mock_session)

    find_mock.assert_not_awaited()
    bot.set_group_ban.assert_not_awaited()


@pytest.mark.asyncio
async def test_ignores_ban_with_zero_duration(mock_session: Mock) -> None:
    """Duration 为 0 的 ban 事件不触发恢复。"""
    bot = _bot()
    event = _ban_event(duration=0)

    with patch.object(module, "find_active_subject_policy", AsyncMock()) as find_mock:
        await module.handle_group_ban_notice(bot, event, mock_session)

    find_mock.assert_not_awaited()
    bot.set_group_ban.assert_not_awaited()


@pytest.mark.asyncio
async def test_ignores_non_protected_user(mock_session: Mock) -> None:
    """非保护用户不触发恢复。"""
    bot = _bot()
    event = _ban_event()

    with (
        patch.object(
            module, "find_active_subject_policy", AsyncMock(return_value=None)
        ),
        patch.object(module, "operator_is_superuser_onebot11", AsyncMock()),
    ):
        await module.handle_group_ban_notice(bot, event, mock_session)

    bot.set_group_ban.assert_not_awaited()


@pytest.mark.asyncio
async def test_skips_when_whole_group_muted(mock_session: Mock) -> None:
    """全体禁言期间不恢复（无法单独解禁个人）。"""
    bot = _bot()
    event = _ban_event()

    with (
        patch.object(
            module,
            "find_active_subject_policy",
            new=AsyncMock(return_value=SimpleNamespace()),
        ),
        patch.object(module, "operator_is_superuser_onebot11", AsyncMock()),
        patch.object(module, "_is_whole_group_muted", new=AsyncMock(return_value=True)),
    ):
        await module.handle_group_ban_notice(bot, event, mock_session)

    bot.set_group_ban.assert_not_awaited()


@pytest.mark.asyncio
async def test_skips_superuser_muting_normal_member(mock_session: Mock) -> None:
    """超级用户禁言非同级（非超级用户）的受保护用户 → 强制生效不恢复。"""
    bot = _bot()
    event = _ban_event()

    with (
        patch.object(
            module,
            "find_active_subject_policy",
            new=AsyncMock(return_value=SimpleNamespace()),
        ),
        patch.object(
            module,
            "operator_is_superuser_onebot11",
            new=AsyncMock(side_effect=lambda _s, uid: uid == _OPERATOR_ID),
        ),
        patch.object(
            module, "_is_whole_group_muted", new=AsyncMock(return_value=False)
        ),
    ):
        await module.handle_group_ban_notice(bot, event, mock_session)

    bot.set_group_ban.assert_not_awaited()


@pytest.mark.asyncio
async def test_restores_superuser_muting_superuser(mock_session: Mock) -> None:
    """超级用户禁言同为超级用户的受保护用户 → 恢复。"""
    bot = _bot()
    event = _ban_event()

    with (
        patch.object(
            module,
            "find_active_subject_policy",
            new=AsyncMock(return_value=SimpleNamespace()),
        ),
        patch.object(
            module,
            "operator_is_superuser_onebot11",
            new=AsyncMock(return_value=True),
        ),
        patch.object(
            module, "_is_whole_group_muted", new=AsyncMock(return_value=False)
        ),
    ):
        await module.handle_group_ban_notice(bot, event, mock_session)

    bot.set_group_ban.assert_awaited_once_with(
        group_id=_GROUP_ID,
        user_id=_PROTECTED_USER_ID,
        duration=0,
    )


@pytest.mark.asyncio
async def test_handles_api_failure_gracefully(mock_session: Mock) -> None:
    """解禁 API 被拒绝时不抛错。"""
    bot = _bot()
    bot.set_group_ban = AsyncMock(side_effect=OneBot11ActionFailed())
    event = _ban_event()

    with (
        patch.object(
            module,
            "find_active_subject_policy",
            new=AsyncMock(return_value=SimpleNamespace()),
        ),
        patch.object(
            module, "operator_is_superuser_onebot11", AsyncMock(return_value=False)
        ),
        patch.object(
            module, "_is_whole_group_muted", new=AsyncMock(return_value=False)
        ),
        patch.object(
            module, "_fire_protect_restore_audit", new=MagicMock()
        ) as audit_mock,
    ):
        await module.handle_group_ban_notice(bot, event, mock_session)

    audit_mock.assert_not_called()


@pytest.mark.asyncio
async def test_whole_group_muted_detection_future_timestamp() -> None:
    """Bot 自身未来禁言时间戳 → 视为全体禁言。"""
    import time

    bot = _bot()
    bot.get_group_member_info = AsyncMock(
        return_value={"shut_up_timestamp": int(time.time()) + 3600}
    )

    assert await module._is_whole_group_muted(bot, _GROUP_ID) is True


@pytest.mark.asyncio
async def test_whole_group_muted_detection_zero_timestamp() -> None:
    """shut_up_timestamp 为 0 → 非全体禁言。"""
    bot = _bot()
    bot.get_group_member_info = AsyncMock(return_value={"shut_up_timestamp": 0})

    assert await module._is_whole_group_muted(bot, _GROUP_ID) is False


@pytest.mark.asyncio
async def test_whole_group_muted_detection_past_timestamp() -> None:
    """过去的禁言时间戳 → 非全体禁言。"""
    import time

    bot = _bot()
    bot.get_group_member_info = AsyncMock(
        return_value={"shut_up_timestamp": int(time.time()) - 60}
    )

    assert await module._is_whole_group_muted(bot, _GROUP_ID) is False


@pytest.mark.asyncio
async def test_whole_group_muted_detection_api_failure() -> None:
    """查询 bot 自身信息失败 → 保守返回 False。"""
    bot = _bot()
    bot.get_group_member_info = AsyncMock(side_effect=OneBot11ActionFailed())

    assert await module._is_whole_group_muted(bot, _GROUP_ID) is False
